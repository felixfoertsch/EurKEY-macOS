document.addEventListener("DOMContentLoaded", () => {
	const tabs = document.querySelectorAll(".tab");
	const viewer = document.getElementById("pdf-viewer");
	const download = document.getElementById("pdf-download");

	tabs.forEach(tab => {
		tab.addEventListener("click", () => {
			tabs.forEach(t => t.classList.remove("active"));
			tab.classList.add("active");
			const version = tab.dataset.version;
			const url = `pdf/eurkey-${version}-layout.pdf`;
			viewer.src = url;
			download.href = url;
		});
	});
});
