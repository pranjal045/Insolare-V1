# grok code
import hashlib
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from data_pipeline.preprocessing.run_pipeline import run_pipeline

logging.basicConfig(level=logging.INFO)
BASE_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
LOG_FILE = BASE_DIR / "data_pipeline/ingestion/tender_log.json"
RAW_DIR = BASE_DIR / "raw_document"
OUTPUT_DIR = BASE_DIR / "structured_output"

RAW_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
]


def create_session():
    session = requests.Session()
    retries = Retry(
        total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def load_log():
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > 0:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_log(log_data):
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=4)


def download_file(url, save_path, session):
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        response = session.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(response.content)
        return True
    except Exception as e:
        logging.error(f"Failed to download {url}: {e}")
        return False


def get_subpage_links(base_url, soup, session, max_pages=3):
    subpage_links = []
    pagination_links = soup.find_all(
        "a",
        href=True,
        string=lambda t: t and any(kw in t.lower() for kw in ["next", "more", "page"]),
    )

    for link in pagination_links[:max_pages]:
        href = link["href"]
        full_url = urljoin(base_url, href)
        try:
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            response = session.get(full_url, headers=headers, timeout=30, verify=False)
            response.raise_for_status()
            subpage_soup = BeautifulSoup(response.text, "html.parser")
            subpage_links.append((full_url, subpage_soup))
            time.sleep(random.uniform(1, 3))  # Polite delay
        except Exception as e:
            logging.warning(f"Failed to fetch subpage {full_url}: {e}")

    return subpage_links


def find_tender_links(base_url, soup, session, visited=None, depth=0, max_depth=2):
    if visited is None:
        visited = set()
    tender_links = []
    if depth > max_depth:
        return tender_links

    for link in soup.find_all("a", href=True):
        href = link["href"]
        full_url = urljoin(base_url, href)
        if full_url in visited:
            continue
        visited.add(full_url)

        # Heuristic: look for links likely to be tenders
        if any(ext in href.lower() for ext in [".pdf", ".doc", ".docx", ".html#"]):
            tender_links.append((full_url, link))
        elif base_url in full_url and not any(
            x in href.lower() for x in ["login", "register", "signup", "pay", "cart"]
        ):
            try:
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                response = session.get(
                    full_url, headers=headers, timeout=30, verify=False
                )
                response.raise_for_status()
                sub_soup = BeautifulSoup(response.text, "html.parser")
                # Recursively search for tender links
                tender_links.extend(
                    find_tender_links(full_url, sub_soup, session, visited, depth + 1, max_depth)
                )
                time.sleep(random.uniform(0.5, 2))
            except Exception as e:
                logging.warning(f"Failed to crawl {full_url}: {e}")

    return tender_links


def scrape_tender_site(source_url, source_name, log, session):
    logging.info(f"🔍 Scraping {source_name} ({source_url})...")
    new_docs = []

    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        response = session.get(source_url, headers=headers, timeout=30, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Recursively find all tender links
        tender_links = find_tender_links(source_url, soup, session)
        if not tender_links:
            logging.warning(f"No tender documents found on {source_url}")

        for full_url, link in tender_links:
            doc_id = hashlib.md5(full_url.encode()).hexdigest()
            if doc_id in log:
                continue

            # Check for login/payment requirement
            if any(x in full_url.lower() for x in ["login", "register", "signup", "pay", "cart"]):
                logging.error(f"❌ Cannot download {full_url}: Login or payment required.")
                log[doc_id] = {
                    "source": source_name,
                    "title": link.get_text(strip=True)[:100] or f"{source_name} Document",
                    "url": full_url,
                    "timestamp": str(datetime.utcnow()),
                    "downloaded": False,
                    "reason": "Login or payment required",
                }
                continue

            extension = full_url.split(".")[-1].split("?")[0]
            filename = f"{source_name.lower().replace(' ', '_')}_{doc_id}.{extension}"
            save_path = RAW_DIR / filename

            if download_file(full_url, save_path, session):
                log[doc_id] = {
                    "source": source_name,
                    "title": link.get_text(strip=True)[:100] or f"{source_name} Document",
                    "url": full_url,
                    "timestamp": str(datetime.utcnow()),
                    "downloaded": True,
                    "paid": False,
                }
                run_pipeline(save_path, OUTPUT_DIR)
                new_docs.append(doc_id)
                time.sleep(random.uniform(0.5, 2))

    except Exception as e:
        logging.error(f"Error scraping {source_name}: {e}")
        error_doc_id = f"{source_name.lower().replace(' ', '_')}_error"
        if error_doc_id not in log:
            log[error_doc_id] = {
                "source": source_name,
                "title": f"{source_name} Scraping Error",
                "url": source_url,
                "timestamp": str(datetime.utcnow()),
                "downloaded": False,
                "error": str(e),
            }
        new_docs.append(error_doc_id)

    return new_docs


if __name__ == "__main__":
    logging.info("🚀 Starting Tender Documents Scraper")

    # Load tender sources
    source_list = {
        "Source": [
            "https://pudutenders.gov.in",
            "https://assamtenders.gov.in",
            "https://eprocurebel.co.in",
            "https://jharkhandtenders.gov.in",
            "https://eproc.punjab.gov.in",
            "https://tenders.ladakh.gov.in",
            "https://etender.up.nic.in",
            "https://eprocurentpc.nic.in",
            "https://sikkimtender.gov.in",
            "https://coalindiatenders.nic.in",
            "https://etenders.chd.nic.in",
            "https://tender.nprocure.com",
            "https://arunachaltenders.gov.in",
            "https://tendersutl.gov.in",
            "https://etenders.hry.nic.in",
            "https://etenders.gov.in",
            "https://mizoramtenders.gov.in",
            "https://tripuratenders.gov.in",
            "https://ddtenders.gov.in",
            "https://eprocure.goa.gov.in",
            "https://mahatenders.gov.in",
            "https://hptenders.gov.in",
            "https://eprocurehsl.nic.in",
            "https://mptenders.gov.in",
            "https://pmgsytenders.gov.in",
            "https://nagalandtenders.gov.in",
            "https://tntenders.gov.in",
            "https://manipurtenders.gov.in",
            "https://etenders.kerala.gov.in",
            "https://eproc.rajasthan.gov.in",
            "https://iocletenders.nic.in",
            "https://wbtenders.gov.in",
            "https://jktenders.gov.in",
            "https://eprocuregsl.nic.in",
            "https://eprocure.andaman.gov.in",
            "https://eprocuremdl.nic.in",
            "https://tendersodisha.gov.in",
            "https://eprocuremidhani.nic.in",
            "https://eprocuregrse.co.in",
            "https://eproc2.bihar.gov.in",
            "https://cpcletenders.nic.in",
            "https://meghalayatenders.gov.in",
            "https://dnhtenders.gov.in",
            "https://eprocurebhel.co.in",
            "https://defproc.gov.in",
            "https://govtprocurement.delhi.gov.in",
            "https://eprocure.gov.in",
            "https://www.seci.co.in/",
            "https://tender.telangana.gov.in",
            "https://tender.apeprocurement.gov.in",
            "https://eproc2.bihar.gov.in/EPSV2Web/",
            "https://eprocure.gov.in/cppp/latestactivet/endersnew/cpppdata",  # check
        ],
        "Location": [
            "Puducherry",
            "Assam",
            "Bharat Electronics Limited",
            "Jharkhand",
            "Punjab",
            "Ladakh",
            "Uttar Pradesh",
            "NTPC",
            "Sikkim",
            "Coal India",
            "Chandigarh",
            "Gujrat",
            "Arunachal Pradesh",
            "Uttarakhand",
            "Haryana",
            "Government of India",
            "Mizoram",
            "Tripura",
            "Dadra & Nagar Haveli & Daman & Diu",
            "Goa",
            "Maharashtra",
            "Himachal Pradesh",
            "Hindustan Shipyard Limited",
            "Madhya Pradesh",
            "Central (PMGSY)",
            "Nagaland",
            "Tamil Nadu",
            "Manipur",
            "Kerala",
            "Rajasthan",
            "Indian Oil Corporation Limited",
            "West Bengal",
            "Jammu & Kashmir",
            "GSL",
            "Andaman and Nicobar Islands",
            "MDL",
            "Odisha",
            "Midhani",
            "GRSE",
            "Bihar",
            "CP Website",
            # Placeholders for missing locations
            "Placeholder 1",
            "Placeholder 2",
            "Placeholder 3",
            "Placeholder 4",
            "Placeholder 5",
            "Placeholder 6",
            "Placeholder 7",
            "Placeholder 8",
            "Placeholder 9",
            "Placeholder 10",
            "Placeholder 11",
        ],
    }

    print(f"Length of Source list: {len(source_list['Source'])}")
    print(f"Length of Location list: {len(source_list['Location'])}")
    if len(source_list["Source"]) != len(source_list["Location"]):
        raise ValueError("Source and Location lists must be of the same length!")

    tender_sources = [
        {"Source": row["Source"], "Location": row["Location"]}
        for _, row in pd.DataFrame(source_list).iterrows()
    ]

    tender_log = load_log()
    session = create_session()
    total_new = 0

    for source in tender_sources:
        source_url = source["Source"]
        source_name = source["Location"]
        new_docs = scrape_tender_site(source_url, source_name, tender_log, session)
        total_new += len(new_docs)
        time.sleep(random.uniform(2, 5))  # Polite delay between sites

    logging.info(f"\n✅ {total_new} new document(s) processed.\n")
    save_log(tender_log)
