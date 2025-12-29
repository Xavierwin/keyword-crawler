import requests
from bs4 import BeautifulSoup
import csv
import re
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import logging
import argparse
import io

# ================== CONFIGURATION ==================
DEFAULT_INPUT = "repo.txt"
DEFAULT_OUTPUT = "keyword_search_results.csv"
SEARCH_KEYWORD = "09/2025"
THREADS = 4  # Reduced from 8 to be more conservative
TIMEOUT = 20
RETRIES = 3

# List of rotating User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
]

# Optional PDF support
try:
    import pypdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# ===================================================

# Logging setup
logging.basicConfig(
    filename="keyword_crawler.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def get_random_headers():
    """Generate headers with random User-Agent to mimic browser."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

def check_url_for_keyword(url, keyword, retries=RETRIES):
    """
    Fetch URL and search for keyword in text content.
    For PDFs, use pypdf if available.
    """
    found = False
    details = ""
    status = "Checked"

    for attempt in range(retries + 1):
        try:
            # Random delay before request (2-5 seconds)
            time.sleep(random.uniform(2, 5))
            
            headers = get_random_headers()
            resp = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
            
            # Handle blocking explicitly
            if resp.status_code in [403, 429]:
                logging.warning(f"[BLOCK] {url} - Status {resp.status_code}. Pausing...")
                time.sleep(random.uniform(30, 60)) # Long pause if blocked
                if attempt < retries:
                    continue
                else:
                    return url, False, f"Blocked (Status {resp.status_code})", "Error"

            resp.raise_for_status()
            
            content_type = resp.headers.get('Content-Type', '').lower()
            
            # Case 1: PDF Files
            if 'application/pdf' in content_type or url.lower().endswith('.pdf'):
                if not PDF_SUPPORT:
                    return url, False, "Skipped (PDF lib missing)", "PDF"
                
                try:
                    with io.BytesIO(resp.content) as open_pdf_file:
                        reader = pypdf.PdfReader(open_pdf_file)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() + "\n"
                        
                        # Normalize text for search (handle "Top-Up" vs "Top Up")
                        search_text = text.replace('-', ' ').replace('–', ' ') # Handle hyphen and en-dash
                        
                        if keyword in text:
                            found = True
                            count = text.count(keyword)
                            details = f"Found {count} times in PDF"
                        elif keyword in search_text:
                            found = True
                            count = search_text.count(keyword)
                            details = f"Found ~{count} times in PDF (normalized)"
                        else:
                            details = "Not found in PDF"
                            
                    return url, found, details, "PDF"
                    
                except Exception as e:
                    return url, False, f"PDF Error: {str(e)}", "PDF"

            # Case 2: HTML/Text Files
            else:
                soup = BeautifulSoup(resp.text, "html.parser")
                text = soup.get_text()
                
                # Normalize text for search
                search_text = text.replace('-', ' ').replace('–', ' ')
                
                if keyword in text:
                    found = True
                    count = text.count(keyword)
                    details = f"Found {count} times in HTML"
                    logging.info(f"[MATCH] {url} - MATCH FOUND")
                elif keyword in search_text:
                    found = True
                    count = search_text.count(keyword)
                    details = f"Found ~{count} times in HTML (normalized)"
                    logging.info(f"[MATCH] {url} - MATCH FOUND")
                else:
                    details = "Not found"
                
                return url, found, details, "HTML"

        except Exception as e:
            if attempt < retries:
                time.sleep(random.uniform(2, 5))
                continue
            logging.error(f"[ERROR] {url} - Error: {e}")
            return url, False, f"Error: {str(e)}", "Error"

    return url, False, "Max retries exceeded", "Error"


def main():
    parser = argparse.ArgumentParser(description=f"Search for '{SEARCH_KEYWORD}' in repo")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input file with URLs")
    parser.add_argument("--limit", type=int, help="Limit number of URLs to scan (for testing)")
    args = parser.parse_args()
    
    input_file = args.input
    
    if not PDF_SUPPORT:
        print("WARNING: `pypdf` is not installed. PDF files will be skipped.")
        print("    To enable PDF search, run: pip install pypdf")
        logging.warning("pypdf not installed - skipping PDF content search")

    # Load URLs
    if not os.path.exists(input_file):
        print(f"Input file not found: {input_file}")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    # De-duplicate input URLs inside the script
    original_count = len(urls)
    # Use dict.fromkeys to preserve order while removing duplicates
    urls = list(dict.fromkeys(urls))
    if len(urls) < original_count:
        print(f"Removed {original_count - len(urls)} duplicate URLs from input list.")

    # Load already processed URLs to allow resuming
    processed_urls = set()
    if os.path.exists(DEFAULT_OUTPUT):
        with open(DEFAULT_OUTPUT, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            next(reader, None) # Skip header
            for row in reader:
                if row:
                    processed_urls.add(row[0])

    # Filter out processed URLs
    urls = [u for u in urls if u not in processed_urls]
    
    if args.limit:
        urls = urls[:args.limit]
        print(f"LIMITING run to first {args.limit} URLs")

    print(f"Starting search for '{SEARCH_KEYWORD}' in {len(urls)} URLs...")
    print(f"Skipping {len(processed_urls)} previously processed URLs.")
    print(f"Threads: {THREADS}")
    print("Anti-blocking enabled: Random User-Agents & Delays active.")

    results = []
    
    # Check if output exists to write header
    write_header = not os.path.exists(DEFAULT_OUTPUT)
    
    with open(DEFAULT_OUTPUT, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if write_header:
            writer.writerow(["URL", "Type", "Found Keyword", "Details"])

        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            future_to_url = {executor.submit(check_url_for_keyword, url, SEARCH_KEYWORD): url for url in urls}
            
            count_processed = 0
            count_found = 0
            
            for future in as_completed(future_to_url):
                url, found, details, content_type = future.result()
                count_processed += 1
                
                status_icon = "CHECK" # Just internal var
                if found:
                    count_found += 1
                    print(f"FOUND: {url} ({details})")
                    writer.writerow([url, content_type, "YES", details])
                    csvfile.flush() # flush immediately to save progress
                else:
                    writer.writerow([url, content_type, "NO", details])
                
                if count_processed % 5 == 0:
                    print(f"   Processed {count_processed}/{len(urls)}... (Found: {count_found})")

    print(f"\nFinished processing {len(urls)} URLs.")
    print(f"found {count_found} matches.")
    print(f"Results saved to {DEFAULT_OUTPUT}")

if __name__ == "__main__":
    main()
