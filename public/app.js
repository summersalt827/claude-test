(() => {
  const select = document.getElementById("date-select");
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");
  const contentEl = document.getElementById("content");
  let dates = [];
  let data = {};
  let currentIndex = 0;

  async function init() {
    try {
      const res = await fetch("/reports.json");
      const json = await res.json();
      dates = json.reports || [];
      data = json.data || {};
    } catch {
      contentEl.innerHTML = '<p class="error-msg">无法加载日报数据</p>';
      return;
    }

    if (!dates.length) {
      contentEl.innerHTML = '<p class="error-msg">暂无日报数据</p>';
      return;
    }

    dates.forEach((d) => {
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d;
      select.appendChild(opt);
    });

    const hashDate = location.hash.replace("#date=", "");
    const hashIdx = dates.indexOf(hashDate);
    if (hashIdx !== -1) currentIndex = hashIdx;

    select.addEventListener("change", () => {
      currentIndex = dates.indexOf(select.value);
      if (currentIndex === -1) currentIndex = 0;
      showReport(dates[currentIndex]);
    });

    prevBtn.addEventListener("click", () => {
      if (currentIndex < dates.length - 1) {
        currentIndex++;
        showReport(dates[currentIndex]);
      }
    });

    nextBtn.addEventListener("click", () => {
      if (currentIndex > 0) {
        currentIndex--;
        showReport(dates[currentIndex]);
      }
    });

    showReport(dates[currentIndex]);
  }

  function showReport(date) {
    select.value = date;
    location.hash = `date=${date}`;
    prevBtn.disabled = currentIndex >= dates.length - 1;
    nextBtn.disabled = currentIndex <= 0;

    const content = data[date];
    if (!content) {
      contentEl.innerHTML = '<p class="error-msg">该日期暂无日报</p>';
      return;
    }
    if (typeof marked !== "undefined") {
      contentEl.innerHTML = marked.parse(content);
    } else {
      contentEl.innerHTML = `<pre style="white-space:pre-wrap;font-size:14px;">${escapeHtml(content)}</pre>`;
    }
  }

  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  init();
})();
