/* EurKEY interactive keyboard viewer */

const KEYBOARD_ROWS = [
	[
		[10, 1.0, "§"], [18, 1.0, "1"], [19, 1.0, "2"], [20, 1.0, "3"],
		[21, 1.0, "4"], [23, 1.0, "5"], [22, 1.0, "6"], [26, 1.0, "7"],
		[28, 1.0, "8"], [25, 1.0, "9"], [29, 1.0, "0"], [27, 1.0, "-"],
		[24, 1.0, "="], [null, 1.5, "⌫"],
	],
	[
		[null, 1.5, "⇥"], [12, 1.0, "Q"], [13, 1.0, "W"], [14, 1.0, "E"],
		[15, 1.0, "R"], [17, 1.0, "T"], [16, 1.0, "Y"], [32, 1.0, "U"],
		[34, 1.0, "I"], [31, 1.0, "O"], [35, 1.0, "P"], [33, 1.0, "["],
		[30, 1.0, "]"], ["spacer", 1.0, ""],
	],
	[
		[null, 1.75, "⇪"], [0, 1.0, "A"], [1, 1.0, "S"], [2, 1.0, "D"],
		[3, 1.0, "F"], [5, 1.0, "G"], [4, 1.0, "H"], [38, 1.0, "J"],
		[40, 1.0, "K"], [37, 1.0, "L"], [41, 1.0, ";"], [39, 1.0, "'"],
		[42, 1.0, "\\"], ["enter", 0.75, "⏎"],
	],
	[
		[null, 1.25, "⇧"], [50, 1.0, "`"], [6, 1.0, "Z"], [7, 1.0, "X"],
		[8, 1.0, "C"], [9, 1.0, "V"], [11, 1.0, "B"], [45, 1.0, "N"],
		[46, 1.0, "M"], [43, 1.0, ","], [47, 1.0, "."], [44, 1.0, "/"],
		[null, 2.25, "⇧"],
	],
	[
		[null, 1.0, "fn"], [null, 1.0, "⌃"], [null, 1.0, "⌥"], [null, 1.25, "⌘"],
		[null, 5.0, ""], [null, 1.25, "⌘"], [null, 1.0, "⌥"],
		["arrow-cluster", 3.0, ""],
	],
];

const MOD_BASE = "0";
const MOD_SHIFT = "1";
const MOD_OPTION = "3";
const MOD_SHIFT_OPTION = "4";

const LAYERS = [
	{ mod: MOD_SHIFT, cls: "key-char--shift" },
	{ mod: MOD_SHIFT_OPTION, cls: "key-char--shift-option" },
	{ mod: MOD_BASE, cls: "key-char--base" },
	{ mod: MOD_OPTION, cls: "key-char--option" },
];

const MOD_LABELS = { "\u21e7": "shift", "\u2325": "option" };

const cache = new Map();
let currentVersion = "v2.0";
let currentData = null;

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

function renderKeyboard(data) {
	const kb = document.getElementById("keyboard");
	clearElement(kb);

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
				topRow.append(spacerL, makeArrowKey("▲"), spacerR);

				const bottomRow = document.createElement("div");
				bottomRow.className = "arrow-row";
				for (const sym of ["◀", "▼", "▶"]) {
					bottomRow.appendChild(makeArrowKey(sym));
				}

				keyEl.append(topRow, bottomRow);
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
					keyEl.addEventListener("click", () => showDeadKeyPanel(data, deadState));
				}
			}

			rowEl.appendChild(keyEl);
		}

		kb.appendChild(rowEl);
	}
}

function showDeadKeyPanel(data, state) {
	const panel = document.getElementById("dead-key-panel");
	const title = document.getElementById("dead-key-title");
	const grid = document.getElementById("dead-key-grid");

	const dk = data.deadKeys[state];
	if (!dk) return;

	const terminator = dk.terminator || data.terminators[state] || "";
	title.textContent = state + " \u2192 " + displayChar(terminator);

	clearElement(grid);
	const compositions = dk.compositions;
	if (!compositions) return;

	for (const [actionId, composed] of Object.entries(compositions)) {
		const action = data.actions[actionId];
		const base = action?.none || actionId;

		const pair = document.createElement("div");
		pair.className = "dead-key-pair";

		const baseSpan = document.createElement("span");
		baseSpan.className = "dead-key-base";
		baseSpan.textContent = displayChar(base);

		const arrow = document.createElement("span");
		arrow.className = "dead-key-arrow";
		arrow.textContent = "\u2192";

		const composedSpan = document.createElement("span");
		composedSpan.className = "dead-key-composed";
		composedSpan.textContent = displayChar(composed);

		pair.appendChild(baseSpan);
		pair.appendChild(arrow);
		pair.appendChild(composedSpan);
		grid.appendChild(pair);
	}

	panel.hidden = false;
	panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
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
	if (shift && option) layer = "shift-option";
	else if (shift) layer = "shift";
	else if (option) layer = "option";

	if (layer) {
		kb.dataset.activeLayer = layer;
	} else {
		delete kb.dataset.activeLayer;
	}
}

document.addEventListener("keydown", (e) => {
	if (e.key === "Shift") activeModifiers.add("shift");
	if (e.key === "Alt") activeModifiers.add("option");
	updateActiveLayer();
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

			document.getElementById("dead-key-panel").hidden = true;
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

document.getElementById("dead-key-close").addEventListener("click", () => {
	document.getElementById("dead-key-panel").hidden = true;
});

initTabs();
loadVersion(currentVersion).then(data => {
	currentData = data;
	renderKeyboard(data);
}).catch(e => {
	console.error("Failed to load initial layout:", e);
	showError("Failed to load layout data.");
});
