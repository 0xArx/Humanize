/* Runs before first paint: marks the page as scripted and picks the theme, so there is no flash. */
(function () {
  var d = document.documentElement;
  d.classList.add("js");
  var t = "light";
  try { t = localStorage.getItem("hz-site-theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"); } catch (e) {}
  var q = new URLSearchParams(location.search).get("theme");
  if (q === "dark" || q === "light") t = q;
  d.setAttribute("data-theme", t);
})();
