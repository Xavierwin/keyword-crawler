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

# ================== CONFIGURATION ==================
DEFAULT_INPUT = "repo.txt"
DEFAULT_OUTPUT = "keyword_search_results.csv"
STATUS_FILE = "crawl_status.json"

SEARCH_KEYWORD = "09/2025"
THREADS = 4
TIMEOUT = 20
RETRIES = 3

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

# ================== LOGGING ==================
logging.basicConfig(
    filename="keyword_crawler.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ================== STATUS ==================
def update_status(**kwargs):
    status = {}
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as f:
            status = json.load(f)

    status.update(kwargs)
    status["last_updated"] = datetime.utcnow().isoformat()

    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)

# ================== HELPERS ==================
def get_headers():
    return {"User-Agent": random.choice(USER_AGENTS)}

def check_url_for_keyword(url, keyword):
    time.sleep(random.uniform(1.5, 3.5))
    try:
        resp = requests.get(url, headers=get_headers(), timeout=TIMEOUT)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "").lower()

        if "pdf" in content_type or url.lower().endswith(".pdf"):
            if not PDF_SUPPORT:
                return url, False, "PDF skipped", "PDF"

            reader = pypdf.PdfReader(io.BytesIO(resp.content))
            text = " ".join(page.extract_text() or "" for page in reader.pages)

        else:
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(" ")

        if keyword in text:
            return url, True, f"Found {text.count(keyword)} times", "PDF" if "pdf" in content_type else "HTML"

        return url, False, "Not found", "PDF" if "pdf" in content_type else "HTML"

    except Exception as e:
        return url, False, f"Error: {e}", "Error"

# ================== MAIN ==================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=DEFAULT_INPUT)
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print("Input file missing")
        return

    with open(args.input) as f:
        urls = list(dict.fromkeys([u.strip() for u in f if u.strip()]))

    update_status(
        state="RUNNING",
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
            futures = [executor.submit(check_url_for_keyword, u, SEARCH_KEYWORD) for u in urls]

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

    update_status(state="COMPLETED")
    print("Crawl completed")

if __name__ == "__main__":
    main()
