import fs from "fs";
import axios from "axios";
import * as cheerio from "cheerio";
import pdf from "pdf-parse";
import { createObjectCsvWriter } from "csv-writer";

// ================= CONFIG =================
const INPUT_FILE = "crawler/repo.txt";
const CONFIG_FILE = "crawler/search_config.json";
const STATUS_FILE = "crawler/crawl_status.json";
const OUTPUT_FILE = "crawler/keyword_search_results.csv";

const THREADS = 5;
const DELAY_MIN = 300;
const DELAY_MAX = 800;
const TIMEOUT = 20000;

// ================= UTILS =================
const sleep = ms => new Promise(r => setTimeout(r, ms));
const randomDelay = () =>
  sleep(Math.random() * (DELAY_MAX - DELAY_MIN) + DELAY_MIN);

const headers = {
  "User-Agent": "Mozilla/5.0 (compatible; KeywordCrawler/1.0)"
};

// ================= STATUS =================
function updateStatus(data) {
  let status = {};

  if (fs.existsSync(STATUS_FILE)) {
    try {
      const raw = fs.readFileSync(STATUS_FILE, "utf-8").trim();
      if (raw) {
        status = JSON.parse(raw);
      }
    } catch (e) {
      // File was being written by another worker — ignore
      status = {};
    }
  }

  const nextStatus = {
    ...status,
    ...data,
    last_updated: new Date().toISOString()
  };

  // Atomic write: write fully in one operation
  fs.writeFileSync(STATUS_FILE, JSON.stringify(nextStatus, null, 2));
}

// ================= LOAD KEYWORD =================
if (!fs.existsSync(CONFIG_FILE)) {
  throw new Error("❌ search_config.json not found");
}

const { search_keyword } = JSON.parse(
  fs.readFileSync(CONFIG_FILE, "utf-8")
);

console.log(`🔍 Searching for keyword: "${search_keyword}"`);

// ================= LOAD URLS =================
if (!fs.existsSync(INPUT_FILE)) {
  throw new Error("❌ repo.txt not found");
}

const urls = [
  ...new Set(
    fs.readFileSync(INPUT_FILE, "utf-8")
      .split("\n")
      .map(u => u.trim())
      .filter(Boolean)
  )
];

// ================= INIT STATUS =================
updateStatus({
  state: "RUNNING",
  keyword: search_keyword,
  total_urls: urls.length,
  processed: 0,
  found: 0,
  current_url: ""
});

// ================= CSV =================
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

// ================= CRAWL =================
async function processUrl(url) {
  await randomDelay();

  try {
    const res = await axios.get(url, {
      headers,
      timeout: TIMEOUT,
      responseType: "arraybuffer"
    });

    let text = "";
    let type = "HTML";

    const contentType = res.headers["content-type"] || "";

    if (contentType.includes("pdf") || url.endsWith(".pdf")) {
      const data = await pdf(res.data);
      text = data.text || "";
      type = "PDF";
    } else {
      const html = res.data.toString("utf-8");
      const $ = cheerio.load(html);
      text = $.text();
    }

    if (text.includes(search_keyword)) {
      const count = text.split(search_keyword).length - 1;
      return {
        url,
        type,
        found: "YES",
        details: `Found ${count} times`
      };
    }

    return { url, type, found: "NO", details: "Not found" };
  } catch (err) {
    return {
      url,
      type: "Error",
      found: "NO",
      details: err.message
    };
  }
}

// ================= WORKER POOL =================
async function run() {
  const queue = [...urls];
  let processed = 0;
  let found = 0;

  const workers = Array.from({ length: THREADS }).map(async () => {
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
        `[${processed}/${urls.length}] ${url} | Found: ${found}`,
        true
      );
    }
  });

  await Promise.all(workers);

  updateStatus({ state: "COMPLETED" });
  console.log("✅ Crawl completed");
}

run();
