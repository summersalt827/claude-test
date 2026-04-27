(() => {
  const select = document.getElementById("date-select");
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");
  const contentEl = document.getElementById("content");
  let dates = [];
  let currentIndex = 0;

  async function init() {
    try {
      const res = await fetch("/api/reports");
      const data = await res.json();
      dates = data.reports || [];
    } catch {
      contentEl.innerHTML = '<p class="error-msg">无法加载日报列表</p>';
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

    // Check URL hash for date
    const hashDate = location.hash.replace("#date=", "");
    const hashIdx = dates.indexOf(hashDate);
    if (hashIdx !== -1) {
      currentIndex = hashIdx;
    }

    select.addEventListener("change", () => {
      currentIndex = dates.indexOf(select.value);
      if (currentIndex === -1) currentIndex = 0;
      loadReport(dates[currentIndex]);
    });

    prevBtn.addEventListener("click", () => {
      if (currentIndex < dates.length - 1) {
        currentIndex++;
        loadReport(dates[currentIndex]);
      }
    });

    nextBtn.addEventListener("click", () => {
      if (currentIndex > 0) {
        currentIndex--;
        loadReport(dates[currentIndex]);
      }
    });

    loadReport(dates[currentIndex]);
  }

  async function loadReport(date) {
    select.value = date;
    location.hash = `date=${date}`;
    prevBtn.disabled = currentIndex >= dates.length - 1;
    nextBtn.disabled = currentIndex <= 0;
    contentEl.innerHTML = '<p class="loading">加载中...</p>';

    try {
      const res = await fetch(`/api/reports?date=${date}`);
      if (!res.ok) throw new Error("not found");
      const data = await res.json();
      renderMarkdown(data.content);
    } catch {
      contentEl.innerHTML = '<p class="error-msg">该日期暂无日报</p>';
    }
  }

  function renderMarkdown(text) {
    if (typeof marked !== "undefined") {
      contentEl.innerHTML = marked.parse(text);
    } else {
      // Fallback: simple pre-formatted rendering
      contentEl.innerHTML = `<pre style="white-space:pre-wrap;font-size:14px;">${escapeHtml(text)}</pre>`;
    }
  }

  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  init();
})();
