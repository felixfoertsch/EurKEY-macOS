#!/usr/bin/env python3
"""Validate .keylayout files against the EurKEY v1.3 reference spec.

Compares each layout version's key mappings and dead key compositions against
the reference, reporting mismatches. Supports per-version exception lists for
intentional differences.

Usage:
	python3 scripts/validate_layouts.py [--verbose]

Exit code 0 if all layouts pass validation, 1 if any unexpected mismatches.
"""

import sys
from pathlib import Path

# import the parser
sys.path.insert(0, str(Path(__file__).parent))
from parse_keylayout import parse_keylayout, TYPING_KEY_CODES, MODIFIER_LABELS, KEY_CODE_NAMES

BUNDLE_DIR = Path(__file__).parent.parent / "EurKey-macOS.bundle" / "Contents" / "Resources"

# modifier indices that contain meaningful typing output
# (exclude index 6 = Command+Option and 7 = Control — these are system shortcuts)
VALIDATED_MODIFIER_INDICES = {"0", "1", "2", "3", "4", "5"}


def load_layout(version):
	"""Parse a keylayout file for the given version string."""
	path = BUNDLE_DIR / f"EurKEY {version}.keylayout"
	if not path.exists():
		print(f"ERROR: {path} not found")
		sys.exit(2)
	return parse_keylayout(str(path))


def compare_key_maps(reference, target, exceptions):
	"""Compare key maps between reference and target layouts.

	Returns a list of (modifier_label, key_name, code, ref_output, target_output) tuples
	for each mismatch that is not in the exceptions list.
	"""
	mismatches = []

	# build terminator→state name maps for dead key comparison
	# build state_name→terminator for both versions
	ref_state_to_term = {name: dk["terminator"] for name, dk in reference["deadKeys"].items()}
	tgt_state_to_term = {name: dk["terminator"] for name, dk in target["deadKeys"].items()}

	for idx_str in VALIDATED_MODIFIER_INDICES:
		ref_km = reference["keyMaps"].get(idx_str, {}).get("keys", {})
		tgt_km = target["keyMaps"].get(idx_str, {}).get("keys", {})
		mod_label = MODIFIER_LABELS.get(int(idx_str), f"Index {idx_str}")

		for code_str in ref_km:
			code = int(code_str)
			if code not in TYPING_KEY_CODES:
				continue

			ref_key = ref_km[code_str]
			tgt_key = tgt_km.get(code_str, {})

			ref_output = ref_key.get("output", "")
			tgt_output = tgt_key.get("output", "")
			ref_dead = ref_key.get("deadKey", "")
			tgt_dead = tgt_key.get("deadKey", "")

			key_name = KEY_CODE_NAMES.get(code, f"code{code}")

			# check for exception
			exc_key = f"{idx_str}:{code_str}"
			if exc_key in exceptions:
				expected = exceptions[exc_key]
				if expected.get("output") == tgt_output or expected.get("deadKey") == tgt_dead:
					continue
				# exception exists but value doesn't match → still a mismatch
				mismatches.append((
					mod_label, key_name, code,
					f"{ref_output or ref_dead} (ref)",
					f"{tgt_output or tgt_dead} (got, expected exception: {expected})",
				))
				continue

			# compare dead keys by terminator (state names may differ)
			if ref_dead or tgt_dead:
				ref_term = ref_state_to_term.get(ref_dead, ref_dead)
				tgt_term = tgt_state_to_term.get(tgt_dead, tgt_dead)
				if ref_term == tgt_term:
					continue  # same dead key, different name
				# dead keys differ
				ref_display = f"[dead: {ref_dead} → {ref_term}]"
				tgt_display = f"[dead: {tgt_dead} → {tgt_term}]" if tgt_dead else tgt_output or "[missing]"
				mismatches.append((mod_label, key_name, code, ref_display, tgt_display))
				continue

			# compare regular outputs
			if ref_output != tgt_output:
				if not tgt_output and not tgt_dead:
					tgt_display = "[missing]"
				else:
					tgt_display = tgt_output
				mismatches.append((mod_label, key_name, code, ref_output, tgt_display))

	return mismatches


def _build_terminator_map(data):
	"""Build a mapping from terminator character → dead key data.

	Different layout versions may use different state names (e.g., "dead: ^" vs "7")
	but the same terminator character. This allows matching by terminator.
	"""
	return {dk["terminator"]: (name, dk) for name, dk in data["deadKeys"].items()}


def _composition_output_set(compositions):
	"""Extract the set of output characters from a dead key's compositions.

	Since action IDs differ between versions (e.g., "a" vs "a61"), we compare
	by the set of output characters produced, not by action ID.
	"""
	return set(compositions.values())


def compare_dead_keys(reference, target, exceptions):
	"""Compare dead key compositions between reference and target.

	Matches dead key states by their terminator character (since state names
	may differ between versions). Compares composition output sets.

	Returns a list of (dead_key_state, detail, ref_value, target_value) tuples.
	"""
	mismatches = []

	ref_by_term = _build_terminator_map(reference)
	tgt_by_term = _build_terminator_map(target)

	for terminator, (ref_name, ref_dk) in ref_by_term.items():
		if ref_name in exceptions.get("_dead_key_skip", []):
			continue

		if terminator not in tgt_by_term:
			mismatches.append((ref_name, "*", "present", "missing"))
			continue

		_, tgt_dk = tgt_by_term[terminator]

		# compare composition output sets
		ref_outputs = _composition_output_set(ref_dk["compositions"])
		tgt_outputs = _composition_output_set(tgt_dk["compositions"])

		only_ref = ref_outputs - tgt_outputs
		only_tgt = tgt_outputs - ref_outputs

		for out in sorted(only_ref):
			exc_key = f"dead:{ref_name}:output:{out}"
			if exc_key not in exceptions:
				mismatches.append((ref_name, f"output {out}", "present", "missing"))

		for out in sorted(only_tgt):
			exc_key = f"dead:{ref_name}:extra:{out}"
			if exc_key not in exceptions:
				mismatches.append((ref_name, f"output {out}", "missing", "present"))

	return mismatches


def format_char_display(c):
	"""Format a character for display."""
	if not c or c in ("[missing]", "missing", "present"):
		return c
	if len(c) == 1:
		cp = ord(c)
		if cp < 0x20 or cp == 0x7F:
			return f"U+{cp:04X}"
	return c


# --- per-version exception definitions ---
# format: {"modifierIndex:keyCode": {"output": "expected_value"}}
# or {"_dead_key_skip": ["state_name", ...]} to skip entire dead key states

# v1.2 predates v1.3 — known differences documented here
V1_2_EXCEPTIONS = {
	# Shift+Option S: v1.2 has § where v1.3 has ẞ (capital sharp s)
	"4:1": {"output": "§"},
	# v1.2 does not have the ¬ (negation) dead key — added in v1.3
	"_dead_key_skip": ["dead: ¬"],
}

# v1.4 differences from v1.3:
# - §/` key (code 10) in Caps/Caps+Option outputs ẞ instead of §
# - ¬ dead key has an extra ¬ composition (self-referencing)
V1_4_EXCEPTIONS = {
	"2:10": {"output": "ẞ"},   # Caps: §/` → ẞ (capital sharp s)
	"5:10": {"output": "ẞ"},   # Caps+Option: §/` → ẞ
	"dead:dead: ¬:extra:¬": True,  # extra ¬ composition in negation dead key
}

# v2.0 is a custom edition — skip validation for now, just document diffs
V2_0_EXCEPTIONS = {
	"_skip_validation": True,
}

VERSIONS = {
	"v1.2": {"file": "v1.2", "exceptions": V1_2_EXCEPTIONS, "label": "EurKEY v1.2"},
	"v1.3": {"file": "v1.3", "exceptions": {}, "label": "EurKEY v1.3 (reference)"},
	"v1.4": {"file": "v1.4", "exceptions": V1_4_EXCEPTIONS, "label": "EurKEY v1.4"},
	"v2.0": {"file": "v2.0", "exceptions": V2_0_EXCEPTIONS, "label": "EurKEY v2.0 (custom)"},
}


def validate_version(version_key, reference):
	"""Validate a single version against the reference. Returns (pass, mismatch_count)."""
	config = VERSIONS[version_key]
	exceptions = config["exceptions"]

	if exceptions.get("_skip_validation"):
		print(f"\n{'='*60}")
		print(f"  {config['label']} — SKIPPED (custom edition)")
		print(f"{'='*60}")
		return True, 0

	target = load_layout(config["file"])

	print(f"\n{'='*60}")
	print(f"  Validating {config['label']} against v1.3 reference")
	print(f"{'='*60}")

	# compare key maps
	key_mismatches = compare_key_maps(reference, target, exceptions)
	dk_mismatches = compare_dead_keys(reference, target, exceptions)

	total = len(key_mismatches) + len(dk_mismatches)

	if key_mismatches:
		print(f"\n  Key mapping mismatches ({len(key_mismatches)}):")
		for mod_label, key_name, code, ref_out, tgt_out in key_mismatches:
			print(f"    {mod_label:>14s} | {key_name:>12s} (code {code:>3d}): "
				f"ref={format_char_display(ref_out)} got={format_char_display(tgt_out)}")

	if dk_mismatches:
		print(f"\n  Dead key mismatches ({len(dk_mismatches)}):")
		for state, action_id, ref_out, tgt_out in dk_mismatches:
			print(f"    {state:>12s} + {action_id}: "
				f"ref={format_char_display(ref_out)} got={format_char_display(tgt_out)}")

	if total == 0:
		print(f"\n  PASS — no unexpected mismatches")
	else:
		print(f"\n  FAIL — {total} unexpected mismatch(es)")

	return total == 0, total


def self_validate(reference):
	"""Validate that v1.3 matches itself (sanity check)."""
	target = load_layout("v1.3")
	key_mismatches = compare_key_maps(reference, target, {})
	dk_mismatches = compare_dead_keys(reference, target, {})
	total = len(key_mismatches) + len(dk_mismatches)
	if total > 0:
		print("INTERNAL ERROR: v1.3 does not match itself!")
		for m in key_mismatches:
			print(f"  key: {m}")
		for m in dk_mismatches:
			print(f"  dead: {m}")
		return False
	print("  Self-check: v1.3 matches itself ✓")
	return True


def main():
	print("EurKEY-macOS Layout Validation")
	print("Reference: EurKEY v1.3")

	# load reference
	reference = load_layout("v1.3")

	# sanity check
	if not self_validate(reference):
		sys.exit(2)

	all_pass = True
	total_mismatches = 0

	for version_key in VERSIONS:
		if version_key == "v1.3":
			continue  # skip self-comparison
		passed, count = validate_version(version_key, reference)
		if not passed:
			all_pass = False
		total_mismatches += count

	print(f"\n{'='*60}")
	if all_pass:
		print("  ALL LAYOUTS PASS ✓")
	else:
		print(f"  VALIDATION FAILED — {total_mismatches} total mismatch(es)")
	print(f"{'='*60}")

	sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
	main()
