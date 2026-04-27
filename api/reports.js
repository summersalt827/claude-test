const fs = require("fs");
const path = require("path");

const INVESTMENT_DIR = path.join(__dirname, "../investment");
const DATE_RE = /^\d{4}-\d{2}-\d{2}\.md$/;

function listReports() {
  if (!fs.existsSync(INVESTMENT_DIR)) return [];
  return fs
    .readdirSync(INVESTMENT_DIR)
    .filter((f) => DATE_RE.test(f))
    .map((f) => f.replace(".md", ""))
    .sort()
    .reverse();
}

function readReport(date) {
  const safe = date.replace(/[^0-9\-]/g, "");
  const file = path.join(INVESTMENT_DIR, `${safe}.md`);
  if (!fs.existsSync(file)) return null;
  return fs.readFileSync(file, "utf-8");
}

module.exports = (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Cache-Control", "s-maxage=300, stale-while-revalidate");

  const url = new URL(req.url, "http://localhost");
  const date = url.searchParams.get("date");

  if (date) {
    const content = readReport(date);
    if (!content) {
      res.writeHead(404, { "Content-Type": "application/json" });
      return res.end(JSON.stringify({ error: "not found" }));
    }
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    return res.end(JSON.stringify({ date, content }));
  }

  const reports = listReports();
  res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify({ reports }));
};
