import requests
from bs4 import BeautifulSoup
import csv
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import logging
import argparse
import io
import json
from datetime import datetime

# ================= CONFIG =================
DEFAULT_INPUT = "repo.txt"
DEFAULT_OUTPUT = "keyword_search_results.csv"
STATUS_FILE = "crawl_status.json"
CONFIG_FILE = "search_config.json"

THREADS = 4
TIMEOUT = 20

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)",
]

try:
    import pypdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# ================= STATUS =================
def update_status(**kwargs):
    status = {}
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as f:
            status = json.load(f)

    status.update(kwargs)
    status["last_updated"] = datetime.utcnow().isoformat()

    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)

# ================= HELPERS =================
def get_headers():
    return {"User-Agent": random.choice(USER_AGENTS)}

def load_search_keyword():
    if not os.path.exists(CONFIG_FILE):
        raise RuntimeError("search_config.json not found")
    with open(CONFIG_FILE) as f:
        return json.load(f).get("search_keyword")

def check_url_for_keyword(url, keyword):
    time.sleep(random.uniform(0.3, 0.8))
    try:
        resp = requests.get(url, headers=get_headers(), timeout=TIMEOUT)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "").lower()

        if "pdf" in content_type or url.lower().endswith(".pdf"):
            if not PDF_SUPPORT:
                return url, False, "PDF skipped", "PDF"
            reader = pypdf.PdfReader(io.BytesIO(resp.content))
            text = " ".join(page.extract_text() or "" for page in reader.pages)
            page_type = "PDF"
        else:
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(" ")
            page_type = "HTML"

        if keyword in text:
            return url, True, f"Found {text.count(keyword)} times", page_type

        return url, False, "Not found", page_type

    except Exception as e:
        return url, False, f"Error: {e}", "Error"

# ================= MAIN =================
def main():
    keyword = load_search_keyword()
    print(f"🔍 Searching for keyword: {keyword}", flush=True)

    with open(DEFAULT_INPUT) as f:
        urls = list(dict.fromkeys([u.strip() for u in f if u.strip()]))

    update_status(
        state="RUNNING",
        keyword=keyword,
        total_urls=len(urls),
        processed=0,
        found=0,
        current_url=""
    )

    write_header = not os.path.exists(DEFAULT_OUTPUT)

    with open(DEFAULT_OUTPUT, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if write_header:
            writer.writerow(["URL", "Type", "Found Keyword", "Details"])

        processed = 0
        found = 0

        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            futures = [
                executor.submit(check_url_for_keyword, u, keyword)
                for u in urls
            ]

            for future in as_completed(futures):
                url, is_found, details, ctype = future.result()
                processed += 1

                if is_found:
                    found += 1
                    writer.writerow([url, ctype, "YES", details])
                else:
                    writer.writerow([url, ctype, "NO", details])

                csvfile.flush()

                update_status(
                    processed=processed,
                    found=found,
                    current_url=url
                )

                print(
                    f"[{processed}/{len(urls)}] {url} | Found: {found}",
                    flush=True
                )

    update_status(state="COMPLETED")
    print("✅ Crawl completed", flush=True)

if __name__ == "__main__":
    main()
