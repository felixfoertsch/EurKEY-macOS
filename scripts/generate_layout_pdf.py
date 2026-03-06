#!/usr/bin/env python3
"""Generate keyboard layout PDFs from .keylayout files.

Renders an ISO keyboard diagram showing Base, Shift, Option, and
Shift+Option layers on each key, plus dead key composition tables.

Requires: fpdf2 (pip install fpdf2)

Usage:
	python3 scripts/generate_layout_pdf.py                  # all versions
	python3 scripts/generate_layout_pdf.py -v v1.3          # specific version
	python3 scripts/generate_layout_pdf.py -o docs/          # custom output dir
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from parse_keylayout import parse_keylayout, TYPING_KEY_CODES

try:
	from fpdf import FPDF
except ImportError:
	print("ERROR: fpdf2 required for PDF generation")
	print("Install with: pip install fpdf2")
	sys.exit(1)


# --- Physical ISO keyboard layout ---
# Each entry: (key_code, width_in_units, physical_label)
# key_code = None for non-typing keys (modifiers, spacers)
KEYBOARD_ROWS = [
	# Row 0: Number row
	[
		(10, 1.0, "§"), (18, 1.0, "1"), (19, 1.0, "2"), (20, 1.0, "3"),
		(21, 1.0, "4"), (23, 1.0, "5"), (22, 1.0, "6"), (26, 1.0, "7"),
		(28, 1.0, "8"), (25, 1.0, "9"), (29, 1.0, "0"), (27, 1.0, "-"),
		(24, 1.0, "="), (None, 1.5, "⌫"),
	],
	# Row 1: QWERTY row (1.0u spacer at end for ISO enter)
	[
		(None, 1.5, "⇥"), (12, 1.0, "Q"), (13, 1.0, "W"), (14, 1.0, "E"),
		(15, 1.0, "R"), (17, 1.0, "T"), (16, 1.0, "Y"), (32, 1.0, "U"),
		(34, 1.0, "I"), (31, 1.0, "O"), (35, 1.0, "P"), (33, 1.0, "["),
		(30, 1.0, "]"), ("spacer", 1.0, ""),
	],
	# Row 2: Home row (0.75u enter spanning into row 1)
	[
		(None, 1.75, "⇪"), (0, 1.0, "A"), (1, 1.0, "S"), (2, 1.0, "D"),
		(3, 1.0, "F"), (5, 1.0, "G"), (4, 1.0, "H"), (38, 1.0, "J"),
		(40, 1.0, "K"), (37, 1.0, "L"), (41, 1.0, ";"), (39, 1.0, "'"),
		(42, 1.0, "\\"), ("enter", 0.75, "⏎"),
	],
	# Row 3: Bottom row
	[
		(None, 1.25, "⇧"), (50, 1.0, "`"), (6, 1.0, "Z"), (7, 1.0, "X"),
		(8, 1.0, "C"), (9, 1.0, "V"), (11, 1.0, "B"), (45, 1.0, "N"),
		(46, 1.0, "M"), (43, 1.0, ","), (47, 1.0, "."), (44, 1.0, "/"),
		(None, 2.25, "⇧"),
	],
	# Row 4: Modifier row
	[
		(None, 1.0, "fn"), (None, 1.0, "⌃"), (None, 1.0, "⌥"),
		(None, 1.25, "⌘"), (None, 5.0, ""),
		(None, 1.25, "⌘"), (None, 1.0, "⌥"),
		("arrows", 3.0, ""),
	],
]

# Modifier layer indices
MOD_BASE = "0"
MOD_SHIFT = "1"
MOD_OPTION = "3"
MOD_SHIFT_OPTION = "4"

# Display layers: (modifier_index, color_rgb, position)
DISPLAY_LAYERS = [
	(MOD_SHIFT, (0, 40, 170), "top_left"),
	(MOD_SHIFT_OPTION, (120, 0, 120), "top_right"),
	(MOD_BASE, (0, 0, 0), "bottom_left"),
	(MOD_OPTION, (170, 0, 0), "bottom_right"),
]

# Layout dimensions (mm)
KU = 20        # key unit size
KEY_GAP = 1    # gap between keys
MARGIN = 10    # page margin
# 15 keys × 20mm = 300mm + 2×10mm margins = 320mm → custom page width
PAGE_W = 320
PAGE_H = 210   # A4 height

# Colors (RGB tuples)
C_KEY_BG = (242, 242, 242)
C_KEY_BORDER = (190, 190, 190)
C_DEAD_BG = (255, 238, 204)
C_MOD_BG = (225, 225, 230)

# Font paths (relative to project root)
FONT_DIR = Path(__file__).parent.parent / "fonts" / "iosevka"
FONT_REGULAR = FONT_DIR / "IosevkaFixed-Regular.ttf"
FONT_BOLD = FONT_DIR / "IosevkaFixed-Bold.ttf"


def safe_char(c):
	"""Format a character for display, handling control chars and blanks."""
	if not c:
		return ""
	if len(c) == 1:
		cp = ord(c)
		if cp < 0x20:
			return f"U+{cp:04X}"
		if cp == 0x7F:
			return ""
		if cp == 0xA0:
			return "NBSP"
	return c


def get_key_info(data, mod_idx, code_str):
	"""Get display character and dead-key status for a key."""
	km = data["keyMaps"].get(mod_idx, {}).get("keys", {})
	key_data = km.get(code_str, {})

	dead_state = key_data.get("deadKey", "")
	if dead_state:
		terminator = data["deadKeys"].get(dead_state, {}).get("terminator", "")
		return safe_char(terminator), True

	return safe_char(key_data.get("output", "")), False


class LayoutPDF(FPDF):
	def __init__(self, layout_name):
		super().__init__(orientation="L", unit="mm", format=(PAGE_H, PAGE_W))
		self.layout_name = layout_name
		self.set_auto_page_break(auto=False)

		if not FONT_REGULAR.exists():
			print(f"ERROR: font not found: {FONT_REGULAR}")
			print("Run: scripts/download-fonts.sh or see fonts/README.md")
			sys.exit(1)

		self.add_font("Iosevka", "", str(FONT_REGULAR))
		if FONT_BOLD.exists():
			self.add_font("Iosevka", "B", str(FONT_BOLD))

	def _font(self, size, bold=False):
		self.set_font("Iosevka", "B" if bold else "", size)

	def _color(self, rgb):
		self.set_text_color(*rgb)

	def generate(self, data):
		"""Generate the full PDF for a layout."""
		self._draw_keyboard_page(data)
		self._draw_dead_key_pages(data)

	def _draw_keyboard_page(self, data):
		self.add_page()

		# title
		self._font(18, bold=True)
		self._color((0, 0, 0))
		self.set_xy(MARGIN, 7)
		self.cell(0, 7, self.layout_name)

		# legend
		self._draw_legend()

		# keyboard
		kb_y = 24
		for row_idx, row in enumerate(KEYBOARD_ROWS):
			x = MARGIN
			y = kb_y + row_idx * KU
			for key_code, width, label in row:
				kw = width * KU - KEY_GAP
				kh = KU - KEY_GAP

				if key_code == "spacer":
					# invisible spacer — just advance x
					pass
				elif key_code == "enter":
					# tall enter key spanning up into previous row
					enter_h = 2 * KU - KEY_GAP
					enter_y = y - KU
					self._draw_mod_key(x, enter_y, kw, enter_h, label, key_code)
				elif key_code == "arrows":
					self._draw_arrow_cluster(x, y, kw, kh)
				elif key_code is None or key_code not in TYPING_KEY_CODES:
					self._draw_mod_key(x, y, kw, kh, label, key_code)
				else:
					self._draw_key(x, y, kw, kh, key_code, data)

				x += width * KU

	def _draw_legend(self):
		y = 17
		x = MARGIN
		self._font(8)
		items = [
			((0, 0, 0), "Base"),
			((0, 40, 170), "Shift"),
			((170, 0, 0), "Option"),
			((120, 0, 120), "Shift+Option"),
		]
		for color, label in items:
			self._color(color)
			self.set_xy(x, y)
			self.cell(0, 4, f"■ {label}")
			x += 26

		# dead key indicator
		self.set_fill_color(*C_DEAD_BG)
		self.set_draw_color(*C_KEY_BORDER)
		self.rect(x, y, 5, 3.5, "DF")
		self._color((0, 0, 0))
		self.set_xy(x + 6, y)
		self.cell(0, 4, "Dead key")

	def _draw_mod_key(self, x, y, w, h, label, key_code):
		"""Draw a modifier/non-typing key."""
		self.set_fill_color(*C_MOD_BG)
		self.set_draw_color(*C_KEY_BORDER)
		self.rect(x, y, w, h, "DF")

		if label:
			self._font(14, bold=True)
			self._color((130, 130, 130))
			self.set_xy(x, y + h / 2 - 3)
			self.cell(w, 6, label, align="C")

	def _draw_arrow_cluster(self, x, y, w, h):
		"""Draw inverted-T arrow keys."""
		arrow_w = w / 3 - KEY_GAP * 0.67
		arrow_h = h / 2 - KEY_GAP * 0.5
		arrows_top = [("", arrow_w), ("▲", arrow_w), ("", arrow_w)]
		arrows_bot = [("◀", arrow_w), ("▼", arrow_w), ("▶", arrow_w)]
		for row_arrows, ay in [(arrows_top, y), (arrows_bot, y + h / 2)]:
			ax = x
			for label, aw in row_arrows:
				if label:
					self.set_fill_color(*C_MOD_BG)
					self.set_draw_color(*C_KEY_BORDER)
					self.rect(ax, ay, aw, arrow_h, "DF")
					self._font(7)
					self._color((130, 130, 130))
					self.set_xy(ax, ay + arrow_h / 2 - 2)
					self.cell(aw, 4, label, align="C")
				ax += aw + KEY_GAP

	def _draw_key(self, x, y, w, h, key_code, data):
		"""Draw a typing key with 4 modifier layers."""
		code_str = str(key_code)
		has_dead = False

		# check if any layer is a dead key
		for mod_idx, _, _ in DISPLAY_LAYERS:
			_, is_dead = get_key_info(data, mod_idx, code_str)
			if is_dead:
				has_dead = True
				break

		# background
		bg = C_DEAD_BG if has_dead else C_KEY_BG
		self.set_fill_color(*bg)
		self.set_draw_color(*C_KEY_BORDER)
		self.rect(x, y, w, h, "DF")

		pad = 1.2
		mid_x = x + w / 2
		mid_y = y + h / 2

		for mod_idx, color, pos in DISPLAY_LAYERS:
			char, is_dead = get_key_info(data, mod_idx, code_str)
			if not char:
				continue

			self._color(color)

			if pos == "bottom_left":
				self._font(14)
				self.set_xy(x + pad, mid_y - 0.5)
				self.cell(w / 2 - pad, h / 2, char)
			elif pos == "top_left":
				self._font(11)
				self.set_xy(x + pad, y + pad)
				self.cell(w / 2 - pad, 5.5, char)
			elif pos == "bottom_right":
				self._font(11)
				self.set_xy(mid_x, mid_y - 0.5)
				self.cell(w / 2 - pad, h / 2, char, align="R")
			elif pos == "top_right":
				self._font(11)
				self.set_xy(mid_x, y + pad)
				self.cell(w / 2 - pad, 5.5, char, align="R")

	# catchy names keyed by terminator character (stable across versions)
	DEAD_KEY_NAMES_BY_TERMINATOR = {
		"´": "The Acutes",
		"`": "The Graves",
		"^": "The Circumflexes",
		"~": "The Tildes",
		"¨": "The Umlauts",
		"ˇ": "The Háčeks",
		"¯": "The Macrons",
		"˚": "The Rings & Dots",
		"α": "The Greeks",
		"√": "The Mathematicians",
		"¬": "The Navigators",
		"©": "The Navigators",
		" ": "The Mathematicians",
	}

	def _find_dead_key_trigger(self, data, state_name):
		"""Find which key combo triggers a dead key state."""
		mod_names = {
			"0": "", "1": "⇧ ", "2": "⇪ ", "3": "⌥ ",
			"4": "⇧⌥ ", "5": "⇪⌥ ",
		}
		# map key codes to physical labels from KEYBOARD_ROWS
		code_labels = {}
		for row in KEYBOARD_ROWS:
			for key_code, _, label in row:
				if isinstance(key_code, int):
					code_labels[str(key_code)] = label
		for mod_idx, km in data["keyMaps"].items():
			for kc, kd in km["keys"].items():
				if kd.get("deadKey") == state_name:
					prefix = mod_names.get(mod_idx, f"mod{mod_idx} ")
					key_label = code_labels.get(kc, f"key{kc}")
					return f"{prefix}{key_label}"
		return state_name

	def _draw_dead_key_pages(self, data):
		"""Draw dead key compositions as full keyboard layouts."""
		dead_keys = data.get("deadKeys", {})
		if not dead_keys:
			return

		actions = data.get("actions", {})

		for state_name in sorted(dead_keys.keys()):
			dk = dead_keys[state_name]
			terminator = dk.get("terminator", "")
			compositions = dk.get("compositions", {})
			if not compositions:
				continue

			# build char → composed lookup
			char_to_composed = {}
			for action_id, composed in compositions.items():
				base = actions.get(action_id, {}).get("none", "")
				if base:
					char_to_composed[base] = composed

			# skip if no compositions mapped
			if not char_to_composed:
				continue

			trigger = self._find_dead_key_trigger(data, state_name)
			catchy = self.DEAD_KEY_NAMES_BY_TERMINATOR.get(terminator, state_name)
			self.add_page()

			# title
			self._font(18, bold=True)
			self._color((0, 0, 0))
			self.set_xy(MARGIN, 7)
			self.cell(0, 7, f"{self.layout_name} — {catchy}  ({trigger}, terminator: {safe_char(terminator)})")

			# draw keyboard with compositions
			kb_y = 24
			for row_idx, row in enumerate(KEYBOARD_ROWS):
				x = MARGIN
				y = kb_y + row_idx * KU
				for key_code, width, label in row:
					kw = width * KU - KEY_GAP
					kh = KU - KEY_GAP

					if key_code == "spacer":
						pass
					elif key_code == "enter":
						enter_h = 2 * KU - KEY_GAP
						enter_y = y - KU
						self._draw_mod_key(x, enter_y, kw, enter_h, label, key_code)
					elif key_code == "arrows":
						self._draw_arrow_cluster(x, y, kw, kh)
					elif not isinstance(key_code, int) or key_code not in TYPING_KEY_CODES:
						self._draw_mod_key(x, y, kw, kh, label, key_code)
					else:
						self._draw_dead_composition_key(
							x, y, kw, kh, key_code, data, char_to_composed,
						)

					x += width * KU

	def _draw_dead_composition_key(self, x, y, w, h, key_code, data, char_to_composed):
		"""Draw a key showing dead key compositions for base and shift layers."""
		code_str = str(key_code)
		km_base = data["keyMaps"].get(MOD_BASE, {}).get("keys", {})
		km_shift = data["keyMaps"].get(MOD_SHIFT, {}).get("keys", {})

		base_char = km_base.get(code_str, {}).get("output", "")
		shift_char = km_shift.get(code_str, {}).get("output", "")

		base_composed = char_to_composed.get(base_char, "")
		shift_composed = char_to_composed.get(shift_char, "")

		# background — highlight if any composition exists
		has_comp = bool(base_composed or shift_composed)
		bg = C_DEAD_BG if has_comp else C_KEY_BG
		self.set_fill_color(*bg)
		self.set_draw_color(*C_KEY_BORDER)
		self.rect(x, y, w, h, "DF")

		pad = 1.2
		mid_y = y + h / 2

		if base_composed:
			self._font(14)
			self._color((0, 0, 0))
			self.set_xy(x + pad, mid_y - 0.5)
			self.cell(w / 2 - pad, h / 2, safe_char(base_composed))
		elif base_char:
			self._font(14)
			self._color((200, 200, 200))
			self.set_xy(x + pad, mid_y - 0.5)
			self.cell(w / 2 - pad, h / 2, safe_char(base_char))

		if shift_composed:
			self._font(11)
			self._color((0, 40, 170))
			self.set_xy(x + pad, y + pad)
			self.cell(w / 2 - pad, 5.5, safe_char(shift_composed))
		elif shift_char:
			self._font(11)
			self._color((200, 200, 200))
			self.set_xy(x + pad, y + pad)
			self.cell(w / 2 - pad, 5.5, safe_char(shift_char))


def generate_pdf(version, output_dir):
	"""Generate a PDF for the given layout version."""
	src_dir = Path(__file__).parent.parent / "src" / "keylayouts"
	keylayout = src_dir / f"EurKEY {version}.keylayout"

	if not keylayout.exists():
		print(f"ERROR: {keylayout} not found")
		return False

	print(f"Generating PDF for EurKEY {version}...")
	data = parse_keylayout(str(keylayout), keyboard_type=0)

	pdf = LayoutPDF(f"EurKEY {version}")
	pdf.generate(data)

	out = Path(output_dir)
	out.mkdir(parents=True, exist_ok=True)
	output_path = out / f"eurkey-{version}-layout.pdf"
	pdf.output(str(output_path))
	print(f"  Written: {output_path}")
	return True


def main():
	parser = argparse.ArgumentParser(description="Generate keyboard layout PDFs")
	parser.add_argument(
		"--version", "-v", nargs="*",
		default=["v1.2", "v1.3", "v1.4", "v2.0"],
		help="Layout versions to generate (default: all)",
	)
	default_output = str(Path(__file__).parent.parent / "build")
	parser.add_argument(
		"--output", "-o", default=default_output,
		help="Output directory (default: build/)",
	)
	args = parser.parse_args()

	success = True
	for version in args.version:
		if not generate_pdf(version, args.output):
			success = False

	sys.exit(0 if success else 1)


if __name__ == "__main__":
	main()
