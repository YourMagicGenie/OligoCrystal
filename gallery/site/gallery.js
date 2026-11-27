// Gallery wall: colour filter and a full-size viewer. The wall works without
// this script (thumbnails link straight to the full image).
document.addEventListener("DOMContentLoaded", () => {
  const wall = document.getElementById("wall");
  const shown = document.getElementById("shown");
  const buttons = [...document.querySelectorAll(".filters button")];
  const viewer = document.getElementById("viewer");
  const img = document.getElementById("viewer-img");
  const cat = document.getElementById("viewer-cat");
  const year = document.getElementById("viewer-year");
  let visible = [];
  let at = -1;

  const items = [...wall.querySelectorAll("li")];

  function applyFilter(colour) {
    visible = [];
    for (const li of items) {
      const on = colour === "all" || li.dataset.colour === colour;
      li.hidden = !on;
      if (on) visible.push(li.querySelector("a"));
    }
    for (const b of buttons) b.setAttribute("aria-pressed", String(b.dataset.colour === colour));
    shown.textContent = colour === "all" ? "" : `· ${visible.length.toLocaleString()} ${colour}`;
  }

  for (const b of buttons) b.addEventListener("click", () => applyFilter(b.dataset.colour));
  applyFilter("all");

  function open(i) {
    at = (i + visible.length) % visible.length;
    const a = visible[at];
    img.src = a.href;
    img.width = +a.dataset.w;
    img.height = +a.dataset.h;
    img.alt = a.querySelector("img").alt;
    cat.textContent = a.dataset.id;
    year.textContent = `· ${a.dataset.year}`;
    if (!viewer.open) viewer.showModal();
    // Warm the neighbours so arrowing feels instant.
    for (const d of [1, -1]) new Image().src = visible[(at + d + visible.length) % visible.length].href;
  }

  wall.addEventListener("click", (e) => {
    const a = e.target.closest("a");
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey) return;
    e.preventDefault();
    open(visible.indexOf(a));
  });

  document.getElementById("viewer-prev").addEventListener("click", () => open(at - 1));
  document.getElementById("viewer-next").addEventListener("click", () => open(at + 1));
  document.getElementById("viewer-close").addEventListener("click", () => viewer.close());
  viewer.addEventListener("click", (e) => { if (e.target === viewer) viewer.close(); });
  viewer.addEventListener("close", () => { if (visible[at]) visible[at].focus(); });
  document.addEventListener("keydown", (e) => {
    if (!viewer.open) return;
    if (e.key === "ArrowRight") open(at + 1);
    if (e.key === "ArrowLeft") open(at - 1);
  });

  // Swipe between crystals on phones.
  let x0 = null;
  viewer.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
  viewer.addEventListener("touchend", (e) => {
    if (x0 === null) return;
    const dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 50) open(at + (dx < 0 ? 1 : -1));
    x0 = null;
  });
});
