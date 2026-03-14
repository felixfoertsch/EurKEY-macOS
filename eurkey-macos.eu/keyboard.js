/* EurKEY interactive keyboard viewer */

const KEYBOARD_ROWS = [
	[
		[10, 1.0, "§"], [18, 1.0, "1"], [19, 1.0, "2"], [20, 1.0, "3"],
		[21, 1.0, "4"], [23, 1.0, "5"], [22, 1.0, "6"], [26, 1.0, "7"],
		[28, 1.0, "8"], [25, 1.0, "9"], [29, 1.0, "0"], [27, 1.0, "-"],
		[24, 1.0, "="], [null, 1.5, "\u232b"],
	],
	[
		[null, 1.5, "\u21e5"], [12, 1.0, "Q"], [13, 1.0, "W"], [14, 1.0, "E"],
		[15, 1.0, "R"], [17, 1.0, "T"], [16, 1.0, "Y"], [32, 1.0, "U"],
		[34, 1.0, "I"], [31, 1.0, "O"], [35, 1.0, "P"], [33, 1.0, "["],
		[30, 1.0, "]"], ["spacer", 1.0, ""],
	],
	[
		[null, 1.75, "\u21ea"], [0, 1.0, "A"], [1, 1.0, "S"], [2, 1.0, "D"],
		[3, 1.0, "F"], [5, 1.0, "G"], [4, 1.0, "H"], [38, 1.0, "J"],
		[40, 1.0, "K"], [37, 1.0, "L"], [41, 1.0, ";"], [39, 1.0, "'"],
		[42, 1.0, "\\"], ["enter", 0.75, "\u23ce"],
	],
	[
		[null, 1.25, "\u21e7"], [50, 1.0, "`"], [6, 1.0, "Z"], [7, 1.0, "X"],
		[8, 1.0, "C"], [9, 1.0, "V"], [11, 1.0, "B"], [45, 1.0, "N"],
		[46, 1.0, "M"], [43, 1.0, ","], [47, 1.0, "."], [44, 1.0, "/"],
		[null, 2.25, "\u21e7"],
	],
	[
		[null, 1.0, "fn"], [null, 1.0, "\u2303"], [null, 1.0, "\u2325"], [null, 1.25, "\u2318"],
		["spacebar", 5.0, ""], [null, 1.25, "\u2318"], [null, 1.0, "\u2325"],
		["arrow-cluster", 3.0, ""],
	],
];

const MOD_BASE = "0";
const MOD_SHIFT = "1";
const MOD_OPTION = "3";
const MOD_OPTION_SHIFT = "4";

const LAYERS = [
	{ mod: MOD_SHIFT, cls: "key-char--shift" },
	{ mod: MOD_OPTION_SHIFT, cls: "key-char--option-shift" },
	{ mod: MOD_BASE, cls: "key-char--base" },
	{ mod: MOD_OPTION, cls: "key-char--option" },
];

const MOD_LABELS = { "\u21e7": "shift", "\u2325": "option" };

/* Browser keyCode → macOS key code mapping (US/ISO QWERTY) */
const BROWSER_TO_MAC = {
	65: 0, 83: 1, 68: 2, 70: 3, 72: 4, 71: 5, 90: 6, 88: 7,
	67: 8, 86: 9, 192: 50, 66: 11, 81: 12, 87: 13, 69: 14, 82: 15,
	89: 16, 84: 17, 49: 18, 50: 19, 51: 20, 52: 21, 54: 22, 53: 23,
	187: 24, 57: 25, 55: 26, 189: 27, 56: 28, 48: 29, 221: 30,
	79: 31, 85: 32, 219: 33, 73: 34, 80: 35, 76: 37, 74: 38,
	222: 39, 75: 40, 186: 41, 220: 42, 188: 43, 191: 44, 78: 45,
	77: 46, 190: 47, 191: 44, 171: 24, 173: 27, 61: 24, 59: 41,
};

const DEAD_KEY_NAMES = {
	"\u00b4": "The Acutes", "`": "The Graves", "^": "The Circumflexes",
	"~": "The Tildes", "\u00a8": "The Umlauts", "\u02c7": "The H\u00e1\u010deks",
	"\u00af": "The Macrons", "\u02da": "The Rings & Dots",
	"\u03b1": "The Greeks", "\u221a": "The Mathematicians",
	"\u00ac": "The Navigators", "\u00a9": "The Navigators",
	" ": "The Mathematicians",
};

const cache = new Map();
let currentVersion = "v2.0";
let currentData = null;
let currentDeadKey = null;
let keyElements = new Map();

async function loadVersion(version) {
	if (cache.has(version)) return cache.get(version);
	const resp = await fetch("data/eurkey-" + version + ".json");
	if (!resp.ok) throw new Error("Failed to load " + version);
	const data = await resp.json();
	cache.set(version, data);
	return data;
}

function charForKey(data, modIndex, keyCode) {
	const keyMap = data.keyMaps[modIndex];
	if (!keyMap) return null;
	const key = keyMap.keys[String(keyCode)];
	if (!key) return null;
	if (key.deadKey) {
		const terminator = data.terminators[key.deadKey] || data.deadKeys[key.deadKey]?.terminator;
		return { char: terminator || "\u25c6", deadKey: key.deadKey };
	}
	return { char: key.output || "" };
}

function displayChar(ch) {
	if (!ch || ch === " ") return "\u00a0";
	if (ch === "\u00a0") return "\u237d";
	return ch;
}

function clearElement(el) {
	while (el.firstChild) el.removeChild(el.firstChild);
}

/* --- Build composition lookup for a dead key --- */

function buildCompositionMap(data, deadState) {
	const dk = data.deadKeys[deadState];
	if (!dk || !dk.compositions) return null;

	const charMap = {};
	for (const [actionId, composed] of Object.entries(dk.compositions)) {
		const action = data.actions[actionId];
		const base = action?.none || actionId;
		if (base) charMap[base] = composed;
	}
	return charMap;
}

/* --- Render keyboard --- */

function renderKeyboard(data) {
	const kb = document.getElementById("keyboard");
	clearElement(kb);
	keyElements.clear();

	for (const row of KEYBOARD_ROWS) {
		const rowEl = document.createElement("div");
		rowEl.className = "keyboard-row";

		for (const [keyCode, width, label] of row) {
			const keyEl = document.createElement("div");
			keyEl.className = "key";
			keyEl.style.setProperty("--w", width);

			if (keyCode === "arrow-cluster") {
				keyEl.classList.add("key--arrow-cluster");

				function makeArrowKey(sym) {
					const ak = document.createElement("div");
					ak.className = "arrow-key key--mod";
					const lbl = document.createElement("span");
					lbl.className = "key-mod-label";
					lbl.textContent = sym;
					ak.appendChild(lbl);
					return ak;
				}

				const topRow = document.createElement("div");
				topRow.className = "arrow-row";
				const spacerL = document.createElement("div");
				spacerL.className = "arrow-key arrow-key--spacer";
				const spacerR = document.createElement("div");
				spacerR.className = "arrow-key arrow-key--spacer";
				topRow.append(spacerL, makeArrowKey("\u25b2"), spacerR);

				const bottomRow = document.createElement("div");
				bottomRow.className = "arrow-row";
				for (const sym of ["\u25c0", "\u25bc", "\u25b6"]) {
					bottomRow.appendChild(makeArrowKey(sym));
				}

				keyEl.append(topRow, bottomRow);
			} else if (keyCode === "spacebar") {
				keyEl.classList.add("key--mod", "key--spacebar");
				const span = document.createElement("span");
				span.className = "key-mod-label";
				span.textContent = label;
				keyEl.appendChild(span);
			} else if (keyCode === "spacer") {
				keyEl.classList.add("key--spacer");
			} else if (keyCode === "enter") {
				keyEl.classList.add("key--mod", "key--enter");
				const span = document.createElement("span");
				span.className = "key-mod-label";
				span.textContent = label;
				keyEl.appendChild(span);
			} else if (keyCode === null) {
				keyEl.classList.add("key--mod");
				if (MOD_LABELS[label]) keyEl.dataset.mod = MOD_LABELS[label];
				const span = document.createElement("span");
				span.className = "key-mod-label";
				span.textContent = label;
				keyEl.appendChild(span);
			} else {
				keyElements.set(keyCode, keyEl);

				let hasDead = false;
				let deadState = null;

				for (const layer of LAYERS) {
					const info = charForKey(data, layer.mod, keyCode);
					const span = document.createElement("span");
					span.className = "key-char " + layer.cls;
					if (info) {
						span.textContent = displayChar(info.char);
						if (info.deadKey) {
							hasDead = true;
							deadState = info.deadKey;
							span.classList.add("key-char--is-dead");
						}
					}
					keyEl.appendChild(span);
				}

				if (hasDead) {
					keyEl.classList.add("key--dead");
					keyEl.dataset.deadKey = deadState;
					keyEl.addEventListener("click", () => toggleDeadKeyMode(deadState));
				}
			}

			rowEl.appendChild(keyEl);
		}

		kb.appendChild(rowEl);
	}
}

/* --- Dead key mode --- */

function toggleDeadKeyMode(deadState) {
	if (currentDeadKey === deadState) {
		exitDeadKeyMode();
	} else {
		enterDeadKeyMode(deadState);
	}
}

function enterDeadKeyMode(deadState) {
	if (!currentData) return;
	const charMap = buildCompositionMap(currentData, deadState);
	if (!charMap) return;

	// clean up previous dead key mode if active
	if (currentDeadKey) exitDeadKeyMode();

	currentDeadKey = deadState;
	const kb = document.getElementById("keyboard");
	kb.classList.add("keyboard--dead-mode");

	// show catchy name on spacebar
	const dk = currentData.deadKeys[deadState];
	const terminator = dk?.terminator || "";
	const catchy = DEAD_KEY_NAMES[terminator] || "";
	const spaceBar = kb.querySelector(".key--spacebar");
	if (spaceBar) {
		spaceBar.querySelector(".key-mod-label").textContent = catchy;
		spaceBar.classList.add("key--spacebar-label");
	}

	for (const [keyCode, keyEl] of keyElements) {
		const codeStr = String(keyCode);
		const baseKey = currentData.keyMaps[MOD_BASE]?.keys[codeStr];
		const shiftKey = currentData.keyMaps[MOD_SHIFT]?.keys[codeStr];
		const baseChar = baseKey?.output || "";
		const shiftChar = shiftKey?.output || "";

		const baseComposed = charMap[baseChar] || "";
		const shiftComposed = charMap[shiftChar] || "";

		const spans = keyEl.querySelectorAll(".key-char");
		// order: shift, option-shift, base, option
		if (spans[0]) spans[0].textContent = displayChar(shiftComposed);
		if (spans[1]) spans[1].textContent = "";
		if (spans[2]) spans[2].textContent = displayChar(baseComposed);
		if (spans[3]) spans[3].textContent = "";

		if (keyEl.dataset.deadKey === deadState) {
			keyEl.classList.add("key--dead-active");
		} else if (baseComposed || shiftComposed) {
			keyEl.classList.add("key--has-composition");
			keyEl.classList.remove("key--no-composition");
		} else {
			keyEl.classList.add("key--no-composition");
			keyEl.classList.remove("key--has-composition");
		}
	}
}

function exitDeadKeyMode() {
	if (!currentDeadKey || !currentData) return;
	currentDeadKey = null;

	const kb = document.getElementById("keyboard");
	kb.classList.remove("keyboard--dead-mode");

	// restore spacebar
	const spaceBar = kb.querySelector(".key--spacebar");
	if (spaceBar) {
		spaceBar.querySelector(".key-mod-label").textContent = "";
		spaceBar.classList.remove("key--spacebar-label");
	}

	// restore original characters
	for (const [keyCode, keyEl] of keyElements) {
		keyEl.classList.remove("key--has-composition", "key--no-composition", "key--dead-active");

		const spans = keyEl.querySelectorAll(".key-char");
		const layerOrder = [MOD_SHIFT, MOD_OPTION_SHIFT, MOD_BASE, MOD_OPTION];
		for (let i = 0; i < spans.length; i++) {
			const info = charForKey(currentData, layerOrder[i], keyCode);
			spans[i].textContent = info ? displayChar(info.char) : "";
		}
	}
}

function showError(msg) {
	const kb = document.getElementById("keyboard");
	clearElement(kb);
	const p = document.createElement("p");
	p.className = "keyboard-error";
	p.textContent = msg;
	kb.appendChild(p);
}

/* --- Modifier key detection --- */

const activeModifiers = new Set();

function updateActiveLayer() {
	const kb = document.getElementById("keyboard");
	const shift = activeModifiers.has("shift");
	const option = activeModifiers.has("option");
	let layer = null;
	if (shift && option) layer = "option-shift";
	else if (shift) layer = "shift";
	else if (option) layer = "option";

	if (layer) {
		kb.dataset.activeLayer = layer;
	} else {
		delete kb.dataset.activeLayer;
	}
}

function getActiveModIndex() {
	const shift = activeModifiers.has("shift");
	const option = activeModifiers.has("option");
	if (shift && option) return MOD_OPTION_SHIFT;
	if (shift) return MOD_SHIFT;
	if (option) return MOD_OPTION;
	return MOD_BASE;
}

document.addEventListener("keydown", (e) => {
	if (e.key === "Shift") activeModifiers.add("shift");
	if (e.key === "Alt") activeModifiers.add("option");
	updateActiveLayer();

	// detect dead key trigger from physical keyboard
	if (currentData && !e.metaKey && !e.ctrlKey) {
		const macCode = BROWSER_TO_MAC[e.keyCode];
		if (macCode !== undefined) {
			const modIdx = getActiveModIndex();
			const keyMap = currentData.keyMaps[modIdx];
			const keyData = keyMap?.keys[String(macCode)];
			if (keyData?.deadKey) {
				e.preventDefault();
				toggleDeadKeyMode(keyData.deadKey);
				return;
			}
		}
	}

	// Escape exits dead key mode
	if (e.key === "Escape" && currentDeadKey) {
		exitDeadKeyMode();
	}
});

document.addEventListener("keyup", (e) => {
	if (e.key === "Shift") activeModifiers.delete("shift");
	if (e.key === "Alt") activeModifiers.delete("option");
	updateActiveLayer();
});

window.addEventListener("blur", () => {
	activeModifiers.clear();
	updateActiveLayer();
});

/* --- Version tabs --- */

function updatePdfLink() {
	const link = document.getElementById("pdf-download");
	if (!link) return;
	link.href = "pdf/eurkey-" + currentVersion + "-layout.pdf";
	link.textContent = "Download " + currentVersion + " PDF";
}

function initTabs() {
	const tabs = document.querySelectorAll(".version-tab");
	tabs.forEach(tab => {
		tab.addEventListener("click", async () => {
			const version = tab.dataset.version;
			if (version === currentVersion) return;

			tabs.forEach(t => t.classList.remove("active"));
			tab.classList.add("active");
			currentVersion = version;
			currentDeadKey = null;

			updatePdfLink();

			try {
				currentData = await loadVersion(version);
				renderKeyboard(currentData);
			} catch (e) {
				console.error("Failed to load layout:", e);
				showError("Failed to load layout data.");
			}
		});
	});
}

/* --- Init --- */

initTabs();
loadVersion(currentVersion).then(data => {
	currentData = data;
	renderKeyboard(data);
}).catch(e => {
	console.error("Failed to load initial layout:", e);
	showError("Failed to load layout data.");
});
