import hashlib
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from data_pipeline.preprocessing.run_pipeline import run_pipeline

logging.basicConfig(level=logging.INFO)
# Change to use local directory path instead of Linux path
BASE_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
LOG_FILE = BASE_DIR / "data_pipeline/ingestion/tender_log.json"
RAW_DIR = BASE_DIR / "raw_document"
OUTPUT_DIR = BASE_DIR / "structured_output"

RAW_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


def load_log():
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > 0:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_log(log_data):
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=4)


def download_file(url, save_path):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(response.content)
        return True
    except Exception as e:
        logging.error(f"Failed to download {url}: {e}")
        return False


# --- MNRE Scraper ---
def scrape_mnre(log):
    logging.info("🌞 Scraping MNRE...")
    url = "https://tender.apeprocurement.gov.in/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    new_docs = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.endswith(".html#"):
            full_url = (
                href
                if href.startswith("http")
                else "https://tender.apeprocurement.gov.in/" + href
            )
            doc_id = hashlib.md5(full_url.encode()).hexdigest()
            if doc_id not in log:
                filename = f"mnre_{doc_id}.pdf"
                save_path = RAW_DIR / filename
                if download_file(full_url, save_path):
                    log[doc_id] = {
                        "source": "MNRE",
                        "title": link.get_text(strip=True)[:100],
                        "url": full_url,
                        "timestamp": str(datetime.utcnow()),
                        "downloaded": True,
                        "paid": False,
                    }
                    run_pipeline(save_path, OUTPUT_DIR)
                    new_docs.append((doc_id, save_path))
    if new_docs:
        logging.info(f"MNRE: Scraped and saved {len(new_docs)} documents:")
        for doc_id, path in new_docs:
            logging.info(f" - {path}")
    else:
        logging.info("MNRE: No new documents scraped.")
    return [doc_id for doc_id, _ in new_docs]


# --- SECI Scraper ---
def scrape_seci(log):
    logging.info("🔆 Scraping SECI...")
    url = "https://www.seci.co.in/Tenders"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    new_docs = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.endswith(".pdf") and "tender" in href.lower():
            full_url = (
                href if href.startswith("http") else "https://www.seci.co.in" + href
            )
            doc_id = hashlib.md5(full_url.encode()).hexdigest()
            if doc_id not in log:
                filename = f"seci_{doc_id}.pdf"
                save_path = RAW_DIR / filename
                if download_file(full_url, save_path):
                    log[doc_id] = {
                        "source": "SECI",
                        "title": link.get_text(strip=True)[:100],
                        "url": full_url,
                        "timestamp": str(datetime.utcnow()),
                        "downloaded": True,
                        "paid": False,
                    }
                    run_pipeline(save_path, OUTPUT_DIR)
                    new_docs.append((doc_id, save_path))
    if new_docs:
        logging.info(f"SECI: Scraped and saved {len(new_docs)} documents:")
        for doc_id, path in new_docs:
            logging.info(f" - {path}")
    else:
        logging.info("SECI: No new documents scraped.")
    return [doc_id for doc_id, _ in new_docs]


# --- IOCL Scraper ---
def scrape_iocl(log):
    logging.info("🛢️ Scraping IOCL...")
    url = "https://iocletenders.nic.in/nicgep/app"
    response = requests.get(url)

    new_docs = []

    try:
        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all(["a", "img"], href=True, src=True):
            if hasattr(link, "href") and link["href"]:
                href = link["href"]
                if any(ext in href.lower() for ext in [".pdf", ".docx", ".doc"]):
                    full_url = href if href.startswith("http") else urljoin(url, href)
                    doc_id = hashlib.md5(full_url.encode()).hexdigest()

                    if doc_id not in log:
                        extension = href.split(".")[-1].lower()
                        filename = f"iocl_{doc_id}.{extension}"
                        save_path = RAW_DIR / filename

                        if download_file(full_url, save_path):
                            log[doc_id] = {
                                "source": "IOCL",
                                "title": (
                                    link.get_text(strip=True)[:100]
                                    if link.get_text(strip=True)
                                    else "IOCL Document"
                                ),
                                "url": full_url,
                                "timestamp": str(datetime.utcnow()),
                                "downloaded": True,
                                "paid": False,
                            }
                            run_pipeline(save_path, OUTPUT_DIR)
                            new_docs.append((doc_id, save_path))

            if hasattr(link, "src") and link["src"]:
                src = link["src"]
                if any(ext in src.lower() for ext in [".jpg", ".jpeg", ".png", ".gif"]):
                    full_url = src if src.startswith("http") else urljoin(url, src)
                    doc_id = hashlib.md5(full_url.encode()).hexdigest()

                    if doc_id not in log:
                        extension = src.split(".")[-1].lower()
                        filename = f"iocl_img_{doc_id}.{extension}"
                        save_path = RAW_DIR / filename

                        if download_file(full_url, save_path):
                            log[doc_id] = {
                                "source": "IOCL",
                                "title": (
                                    link.get("alt", "")[:100]
                                    if link.get("alt")
                                    else "IOCL Image"
                                ),
                                "url": full_url,
                                "timestamp": str(datetime.utcnow()),
                                "downloaded": True,
                                "paid": False,
                            }
                            new_docs.append((doc_id, save_path))

        if not new_docs:
            portal_doc_id = "iocl_portal"
            if portal_doc_id not in log:
                log[portal_doc_id] = {
                    "source": "IOCL",
                    "title": "IOCL Tenders Portal",
                    "url": url,
                    "timestamp": str(datetime.utcnow()),
                    "downloaded": False,
                    "paid": True,
                }
                logging.warning(
                    "🔒 No documents found or documents require payment on IOCL portal"
                )
                new_docs.append((portal_doc_id, None))

    except Exception as e:
        logging.error(f"Error scraping IOCL: {e}")
        error_doc_id = "iocl_error"
        if error_doc_id not in log:
            log[error_doc_id] = {
                "source": "IOCL",
                "title": "IOCL Scraping Error",
                "url": url,
                "timestamp": str(datetime.utcnow()),
                "downloaded": False,
                "error": str(e),
            }
        new_docs.append((error_doc_id, None))

    if new_docs:
        logging.info(f"IOCL: Scraped and saved {len([d for d in new_docs if d[1]])} documents:")
        for doc_id, path in new_docs:
            if path:
                logging.info(f" - {path}")
    else:
        logging.info("IOCL: No new documents scraped.")
    return [doc_id for doc_id, _ in new_docs]


# --- Entry Point ---
if __name__ == "__main__":
    logging.info("🚀 Running Web Scraper for MNRE, SECI & IOCL")
    tender_log = load_log()

    mnre_docs = scrape_mnre(tender_log)
    # seci_docs = scrape_seci(tender_log)
    # iocl_docs = scrape_iocl(tender_log)

    total_new = len(mnre_docs) # + len(seci_docs) + len(iocl_docs)
    logging.info(f"\n✅ {total_new} new document(s) processed.\n")
    save_log(tender_log)
