#!/usr/bin/env python3
"""Parse Apple .keylayout XML files into a flat JSON representation.

Extracts all key mappings across modifier layers (base, Shift, Caps, Option,
Shift+Option, Caps+Option, Command+Option) and resolves dead key states to
their composed outputs.

Usage:
	python3 scripts/parse_keylayout.py <file.keylayout> [--output file.json]

Output JSON structure:
{
	"name": "EurKEY v1.3",
	"modifierMap": { ... },
	"keyMaps": {
		"0": { "label": "Base", "keys": { "0": {"output": "a", ...}, ... } },
		...
	},
	"actions": {
		"a": {
			"none": "a",
			"dead: ^": "â",
			...
		},
		...
	},
	"deadKeys": {
		"dead: ^": { "terminator": "^", "compositions": { "a": "â", "A": "Â", ... } },
		...
	}
}
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# macOS key code → physical key name (US ANSI/ISO layout)
KEY_CODE_NAMES = {
	0: "A", 1: "S", 2: "D", 3: "F", 4: "H", 5: "G",
	6: "Z", 7: "X", 8: "C", 9: "V", 10: "§/`",
	11: "B", 12: "Q", 13: "W", 14: "E", 15: "R",
	16: "Y", 17: "T", 18: "1", 19: "2", 20: "3",
	21: "4", 22: "6", 23: "5", 24: "=", 25: "9",
	26: "7", 27: "-", 28: "8", 29: "0", 30: "]",
	31: "O", 32: "U", 33: "[", 34: "I", 35: "P",
	36: "Return", 37: "L", 38: "J", 39: "'", 40: "K",
	41: ";", 42: "\\", 43: ",", 44: "/", 45: "N",
	46: "M", 47: ".", 48: "Tab", 49: "Space", 50: "`",
	51: "Delete", 52: "Enter", 53: "Escape",
	# numpad
	65: "KP.", 67: "KP*", 69: "KP+", 75: "KP/",
	76: "KPEnter", 78: "KP-", 81: "KP=",
	82: "KP0", 83: "KP1", 84: "KP2", 85: "KP3",
	86: "KP4", 87: "KP5", 88: "KP6", 89: "KP7",
	91: "KP8", 92: "KP9",
	# iso extra key
	93: "ISO§", 94: "ISO_backslash", 95: "ISO_comma",
	# function/navigation keys
	96: "F5", 97: "F6", 98: "F7", 99: "F3",
	100: "F8", 101: "F9", 103: "F11", 105: "F13",
	107: "F14", 109: "F10", 111: "F12", 113: "F15",
	114: "Help/Insert", 115: "Home", 116: "PageUp",
	117: "ForwardDelete", 118: "F4", 119: "End",
	120: "F2", 121: "PageDown", 122: "F1",
	123: "Left", 124: "Right", 125: "Down", 126: "Up",
}

# modifier map index → human-readable label
MODIFIER_LABELS = {
	0: "Base",
	1: "Shift",
	2: "Caps",
	3: "Option",
	4: "Shift+Option",
	5: "Caps+Option",
	6: "Command+Option",
	7: "Control",
}

# key codes that are "typing" keys (not function/navigation/control)
TYPING_KEY_CODES = set(range(0, 50)) | {50, 93, 94, 95}


def _read_keylayout_xml(filepath):
	"""Read a .keylayout file, working around XML 1.1 control character references.

	Apple .keylayout files declare XML 1.1 and use numeric character references
	for control characters (&#x0001; through &#x001F;) that are invalid in XML 1.0.
	Python's ElementTree only supports XML 1.0, so we convert control character
	references to placeholder tokens, parse, then restore them.
	"""
	with open(filepath, "r", encoding="utf-8") as f:
		content = f.read()

	# downgrade XML declaration from 1.1 to 1.0
	content = content.replace('version="1.1"', 'version="1.0"')

	# strip the DOCTYPE (references local DTD that may not exist)
	content = re.sub(r'<!DOCTYPE[^>]*>', '', content)

	# replace control character references with placeholder strings
	# &#x0001; through &#x001F; and &#x007F; are problematic in XML 1.0
	def replace_control_ref(m):
		code_point = int(m.group(1), 16)
		return f"__CTRL_U{code_point:04X}__"

	content = re.sub(
		r'&#x(000[0-9A-Fa-f]|001[0-9A-Fa-f]|007[Ff]);',
		replace_control_ref,
		content,
	)

	return content


def _restore_control_chars(text):
	"""Restore placeholder tokens back to actual characters."""
	if text is None:
		return None

	def restore(m):
		code_point = int(m.group(1), 16)
		return chr(code_point)

	return re.sub(r'__CTRL_U([0-9A-F]{4})__', restore, text)


def parse_keylayout(filepath):
	"""Parse a .keylayout XML file and return a structured dict."""
	xml_content = _read_keylayout_xml(filepath)
	root = ET.fromstring(xml_content)

	result = {
		"name": root.get("name", ""),
		"group": root.get("group", ""),
		"id": root.get("id", ""),
	}

	# parse modifier map
	result["modifierMap"] = parse_modifier_map(root)

	# parse all keyMapSets
	key_map_sets = {}
	for kms in root.findall(".//keyMapSet"):
		kms_id = kms.get("id")
		key_map_sets[kms_id] = parse_key_map_set(kms, key_map_sets)

	# parse actions (dead key compositions)
	actions = parse_actions(root)
	result["actions"] = actions

	# parse terminators
	terminators = {}
	for term in root.findall(".//terminators/when"):
		state = term.get("state", "")
		output = _restore_control_chars(term.get("output", ""))
		terminators[state] = output
	result["terminators"] = terminators

	# resolve layouts
	layouts = root.findall(".//layout")

	# build resolved key maps with all key codes from all layout entries
	resolved = {}
	for layout in layouts:
		map_set_id = layout.get("mapSet")
		first_code = int(layout.get("first", "0"))
		last_code = int(layout.get("last", "0"))
		kms = key_map_sets.get(map_set_id, {})

		for idx_str, keys in kms.items():
			if idx_str not in resolved:
				resolved[idx_str] = {}
			for code_str, entry in keys.items():
				code = int(code_str)
				if first_code <= code <= last_code:
					resolved[idx_str][code_str] = entry

	# build the final keyMaps output
	key_maps = {}
	for idx_str in sorted(resolved.keys(), key=int):
		idx = int(idx_str)
		label = MODIFIER_LABELS.get(idx, f"Index {idx}")
		keys = {}
		for code_str in sorted(resolved[idx_str].keys(), key=int):
			code = int(code_str)
			entry = resolved[idx_str][code_str]
			key_name = KEY_CODE_NAMES.get(code, f"code{code}")
			key_info = {"code": code, "keyName": key_name}

			if "output" in entry:
				key_info["output"] = entry["output"]
			if "action" in entry:
				action_id = entry["action"]
				key_info["action"] = action_id
				# resolve the action's base output
				if action_id in actions:
					action_data = actions[action_id]
					if "none" in action_data:
						key_info["output"] = action_data["none"]
					elif "next" in action_data:
						key_info["deadKey"] = action_data["next"]

			keys[code_str] = key_info
		key_maps[idx_str] = {"label": label, "keys": keys}

	result["keyMaps"] = key_maps

	# build dead key summary
	dead_keys = {}
	for state_name, terminator in terminators.items():
		compositions = {}
		for action_id, action_data in actions.items():
			if state_name in action_data:
				compositions[action_id] = action_data[state_name]
		dead_keys[state_name] = {
			"terminator": terminator,
			"compositions": compositions,
		}
	result["deadKeys"] = dead_keys

	return result


def parse_modifier_map(root):
	"""Parse the modifierMap element."""
	mod_map = {}
	for mm in root.findall(".//modifierMap"):
		mm_id = mm.get("id")
		default_index = mm.get("defaultIndex", "")
		selects = []
		for kms in mm.findall("keyMapSelect"):
			map_index = kms.get("mapIndex", "")
			modifiers = []
			for mod in kms.findall("modifier"):
				modifiers.append(mod.get("keys", ""))
			selects.append({"mapIndex": map_index, "modifiers": modifiers})
		mod_map[mm_id] = {"defaultIndex": default_index, "selects": selects}
	return mod_map


def parse_key_map_set(kms_element, all_key_map_sets):
	"""Parse a keyMapSet element, resolving baseMapSet/baseIndex references."""
	result = {}
	for km in kms_element.findall("keyMap"):
		index = km.get("index")
		keys = {}

		# resolve base map set if specified
		base_map_set_id = km.get("baseMapSet")
		base_index = km.get("baseIndex")
		if base_map_set_id and base_index:
			base_kms = all_key_map_sets.get(base_map_set_id, {})
			base_keys = base_kms.get(base_index, {})
			keys.update(base_keys)

		# parse keys in this keyMap (override base)
		for key in km.findall("key"):
			code = key.get("code")
			entry = {}
			if key.get("output") is not None:
				entry["output"] = _restore_control_chars(key.get("output"))
			if key.get("action") is not None:
				entry["action"] = key.get("action")
			keys[code] = entry

		result[index] = keys
	return result


def parse_actions(root):
	"""Parse all action elements into a dict of action_id → {state → output/next}."""
	actions = {}
	for action in root.findall(".//actions/action"):
		action_id = action.get("id")
		states = {}
		for when in action.findall("when"):
			state = when.get("state", "none")
			if when.get("output") is not None:
				states[state] = _restore_control_chars(when.get("output"))
			elif when.get("next") is not None:
				if state == "none":
					states["next"] = when.get("next")
				else:
					states[state] = f"→{when.get('next')}"
		actions[action_id] = states
	return actions


def format_char(c):
	"""Format a character for display, showing control chars as hex."""
	if len(c) == 1:
		cp = ord(c)
		if cp < 0x20 or cp == 0x7F:
			return f"U+{cp:04X}"
		if cp == 0xA0:
			return "NBSP"
	return c


def print_summary(data):
	"""Print a human-readable summary of the parsed layout."""
	print(f"Layout: {data['name']}")
	print(f"Dead key states: {', '.join(data['deadKeys'].keys())}")
	print()

	for idx_str in sorted(data["keyMaps"].keys(), key=int):
		km = data["keyMaps"][idx_str]
		print(f"--- {km['label']} (index {idx_str}) ---")
		for code_str in sorted(km["keys"].keys(), key=int):
			code = int(code_str)
			if code not in TYPING_KEY_CODES:
				continue
			ki = km["keys"][code_str]
			key_name = ki["keyName"]
			output = ki.get("output", "")
			dead = ki.get("deadKey", "")
			formatted = format_char(output) if output else ""
			extra = f" [dead: {dead}]" if dead else ""
			action = f" (action: {ki['action']})" if "action" in ki else ""
			print(f"  {key_name:>12s} (code {code:>3d}): {formatted}{extra}{action}")
		print()


def main():
	import argparse

	parser = argparse.ArgumentParser(description="Parse Apple .keylayout XML files")
	parser.add_argument("keylayout", help="Path to .keylayout file")
	parser.add_argument("--output", "-o", help="Output JSON file path")
	parser.add_argument("--summary", "-s", action="store_true",
		help="Print human-readable summary")
	args = parser.parse_args()

	data = parse_keylayout(args.keylayout)

	if args.summary:
		print_summary(data)

	if args.output:
		output_path = Path(args.output)
		output_path.parent.mkdir(parents=True, exist_ok=True)
		with open(output_path, "w", encoding="utf-8") as f:
			json.dump(data, f, ensure_ascii=False, indent="\t")
		print(f"Written to {output_path}")
	elif not args.summary:
		json.dump(data, sys.stdout, ensure_ascii=False, indent="\t")
		print()


if __name__ == "__main__":
	main()
