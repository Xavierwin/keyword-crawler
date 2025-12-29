import fs from "fs";
import axios from "axios";
import cheerio from "cheerio";
import pdf from "pdf-parse";
import { createObjectCsvWriter } from "csv-writer";

const INPUT_FILE = "crawler/repo.txt";
const CONFIG_FILE = "crawler/search_config.json";
const STATUS_FILE = "crawler/crawl_status.json";
const OUTPUT_FILE = "crawler/keyword_search_results.csv";

const THREADS = 5;
const DELAY_MIN = 300;
const DELAY_MAX = 800;

const sleep = ms => new Promise(r => setTimeout(r, ms));
const randomDelay = () =>
  sleep(Math.random() * (DELAY_MAX - DELAY_MIN) + DELAY_MIN);

const headers = {
  "User-Agent": "Mozilla/5.0"
};

// 🔁 STATUS UPDATE
function updateStatus(data) {
  let status = {};
  if (fs.existsSync(STATUS_FILE)) {
    status = JSON.parse(fs.readFileSync(STATUS_FILE));
  }
  fs.writeFileSync(
    STATUS_FILE,
    JSON.stringify(
      {
        ...status,
        ...data,
        last_updated: new Date().toISOString()
      },
      null,
      2
    )
  );
}

// 🔍 LOAD KEYWORD
const { search_keyword } = JSON.parse(
  fs.readFileSync(CONFIG_FILE)
);

console.log(`🔍 Searching for keyword: ${search_keyword}`);

// 📄 LOAD URLS
const urls = [...new Set(
  fs.readFileSync(INPUT_FILE, "utf-8")
    .split("\n")
    .map(u => u.trim())
    .filter(Boolean)
)];

updateStatus({
  state: "RUNNING",
  keyword: search_keyword,
  total_urls: urls.length,
  processed: 0,
  found: 0,
  current_url: ""
});

// 🧾 CSV WRITER
const csvWriter = createObjectCsvWriter({
  path: OUTPUT_FILE,
  header: [
    { id: "url", title: "URL" },
    { id: "type", title: "Type" },
    { id: "found", title: "Found Keyword" },
    { id: "details", title: "Details" }
  ],
  append: fs.existsSync(OUTPUT_FILE)
});

let processed = 0;
let found = 0;

// 🌐 FETCH & SEARCH
async function processUrl(url) {
  await randomDelay();

  try {
    const res = await axios.get(url, { headers, timeout: 20000 });
    let text = "";
    let type = "HTML";

    if (
      res.headers["content-type"]?.includes("pdf") ||
      url.endsWith(".pdf")
    ) {
      const data = await pdf(res.data);
      text = data.text;
      type = "PDF";
    } else {
      const $ = cheerio.load(res.data);
      text = $.text();
    }

    if (text.includes(search_keyword)) {
      return {
        url,
        type,
        found: "YES",
        details: `Found ${text.split(search_keyword).length - 1} times`
      };
    }

    return { url, type, found: "NO", details: "Not found" };
  } catch (e) {
    return { url, type: "Error", found: "NO", details: e.message };
  }
}

// ⚙️ WORKER POOL
async function run() {
  const queue = [...urls];
  const workers = new Array(THREADS).fill(null).map(async () => {
    while (queue.length) {
      const url = queue.shift();
      const result = await processUrl(url);

      processed++;
      if (result.found === "YES") found++;

      await csvWriter.writeRecords([result]);

      updateStatus({
        processed,
        found,
        current_url: url
      });

      console.log(
        `[${processed}/${urls.length}] ${url} | Found: ${found}`
      );
    }
  });

  await Promise.all(workers);

  updateStatus({ state: "COMPLETED" });
  console.log("✅ Crawl completed");
}

run();
