/* Festival design add-on. Existing app.js stays untouched. */
(function () {
  "use strict";
  const files = {
    deepavali: "deepavali.jpg",
    cny: "chinese_new_year.jpg",
    raya: "hari_raya.jpg",
    christmas: "christmas.jpg"
  };
  function getTheme() {
    const select = document.getElementById("festival-select");
    if (!select) return "deepavali";
    const opt = select.selectedOptions && select.selectedOptions[0];
    const value = ((select.value || "") + " " + (opt ? opt.textContent : "")).toLowerCase();
    if (value.includes("chinese") || value.includes("lunar") || value.includes("cny")) return "cny";
    if (value.includes("raya") || value.includes("aidilfitri") || value.includes("eid")) return "raya";
    if (value.includes("christmas")) return "christmas";
    return "deepavali";
  }
  function updateTheme() {
    if (!document.body.classList.contains("festival-mode")) {
      document.body.removeAttribute("data-festival-theme");
      document.body.style.removeProperty("--festival-background-image");
      return;
    }
    const key = getTheme();
    document.body.setAttribute("data-festival-theme", key);
    const url = "/static/images/festival_backgrounds/" + files[key];
    document.body.style.setProperty("--festival-background-image", 'url("' + url + '")');
  }
  document.addEventListener("DOMContentLoaded", function () {
    const select = document.getElementById("festival-select");
    if (select) select.addEventListener("change", updateTheme);
    new MutationObserver(updateTheme).observe(document.body, {
      attributes: true, attributeFilter: ["class"]
    });
    updateTheme();
  });
})();
