import json
import logging
import os
import re
import urllib3
import resource
from datetime import datetime
from urllib.parse import urljoin
import subprocess
import sys
import time

# Increase the file descriptor limit to avoid "Too many open files" errors
soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
new_soft_limit = min(hard_limit, 4096)
resource.setrlimit(resource.RLIMIT_NOFILE, (new_soft_limit, hard_limit))

# Set DYLD_LIBRARY_PATH environment variable for macOS to find GTK libraries required by WeasyPrint
os.environ["DYLD_LIBRARY_PATH"] = "/opt/homebrew/lib"

# Install required GTK and related libraries using Homebrew if not already installed
def install_homebrew_packages():
    try:
        # Check if brew is installed
        subprocess.run(["brew", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception:
        logger = logging.getLogger(__name__)
        logger.error("Homebrew is not installed. Please install Homebrew from https://brew.sh and rerun the script.")
        sys.exit(1)

    packages = ["gtk+3", "cairo", "pango", "gdk-pixbuf", "libffi"]
    for pkg in packages:
        try:
            # Check if package is installed
            result = subprocess.run(["brew", "list", pkg], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                # Install package
                print(f"Installing {pkg} via Homebrew...")
                subprocess.run(["brew", "install", pkg], check=True)
        except Exception as e:
            print(f"Failed to install {pkg}: {e}")
            sys.exit(1)

install_homebrew_packages()

import requests
import weasyprint
from bs4 import BeautifulSoup

# Suppress SSL warnings and bypass SSL verification
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
os.environ["WEASYPRINT_SSL_NO_VERIFY"] = "1"

# Setup logging to console (and can be extended to file if needed)
logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Suppress WeasyPrint CSS warnings by setting its logger level to ERROR
logging.getLogger("weasyprint").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# Directories for saving raw documents and structured outputs
RAW_DIR = "raw_document"
STRUCTURED_DIR = "structured_output"
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(STRUCTURED_DIR, exist_ok=True)

# Initialize log data structure
tender_log = {}


def slugify(text):
    """
    Create a filesystem-safe file name from the given text.
    """
    text = text.strip().replace(" ", "_")
    return re.sub(r"[^-\w\.]", "", text)


def download_file(url, save_path):
    """
    Download file from url and save to save_path.
    Returns True if download succeeds, else False.
    """
    try:
        with requests.get(url, stream=True, timeout=30, verify=False) as response:
            response.raise_for_status()
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        print(f"Saved file: {save_path}")
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False


def convert_html_to_pdf(html_content, save_path, base_url=None):
    """
    Convert HTML content to PDF and save to save_path.
    """
    try:
        # Inject base href tag to fix relative URI warnings in WeasyPrint
        if base_url:
            from bs4 import BeautifulSoup as BS
            soup = BS(html_content, "html.parser")
            if not soup.head:
                head_tag = soup.new_tag("head")
                soup.insert(0, head_tag)
            else:
                head_tag = soup.head
            # Check if base tag already exists
            if not head_tag.find("base"):
                base_tag = soup.new_tag("base", href=base_url)
                head_tag.insert(0, base_tag)
            html_content = str(soup)

        # Custom URL fetcher to disable SSL verification for resource loading
        import ssl
        import urllib.request
        import weasyprint.urls

        def custom_url_fetcher(url):
            try:
                skip_exts = ('.woff', '.woff2', '.ttf', '.eot', '.otf', '.svg', '.ico', '.gif')
                skip_patterns = [
                    '/fonts/', '/font/', '/icon', '/favicon', '/apple-touch-icon', '/webfont', '/images/captcha', '/captcha.php'
                ]
                if any(url.lower().endswith(ext) for ext in skip_exts) or any(p in url.lower() for p in skip_patterns):
                    return {"string": b"", "mime_type": "application/octet-stream"}
                if url.startswith("data:"):
                    import base64
                    import re
                    match = re.match(r"data:([^;]+);base64,(.*)", url, re.DOTALL)
                    if match:
                        mime_type, b64_data = match.groups()
                        content = base64.b64decode(b64_data)
                        return {"string": content, "mime_type": mime_type}
                    else:
                        return {"string": b"", "mime_type": "application/octet-stream"}
                context = ssl._create_unverified_context()
                req = urllib.request.Request(url)
                max_redirects = 3
                redirect_count = 0
                current_url = url
                visited_urls = set()
                while redirect_count < max_redirects:
                    if current_url in visited_urls:
                        return {"string": b"", "mime_type": "application/octet-stream"}
                    visited_urls.add(current_url)
                    with urllib.request.urlopen(req, context=context) as response:
                        try:
                            if response.getcode() in (301, 302, 303, 307, 308):
                                redirect_url = response.getheader("Location")
                                if not redirect_url:
                                    break
                                current_url = urllib.parse.urljoin(current_url, redirect_url)
                                req = urllib.request.Request(current_url)
                                redirect_count += 1
                            else:
                                content = response.read()
                                try:
                                    headers = dict(response.getheaders())
                                except AttributeError:
                                    headers = {}
                                mime_type = headers.get("Content-Type", "").split(";")[0]
                                if mime_type == "application/octet-stream":
                                    return {"string": b"", "mime_type": mime_type}
                                return {
                                    "string": content,
                                    "mime_type": mime_type,
                                }
                        finally:
                            response.close()
                return {"string": b"", "mime_type": "application/octet-stream"}
            except Exception:
                return {"string": b"", "mime_type": "application/octet-stream"}

        # Monkeypatch urllib and requests to disable SSL verification globally during PDF conversion
        import urllib3
        import requests
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        old_urlopen = urllib.request.urlopen
        def urlopen_no_ssl_verify(*args, **kwargs):
            kwargs['context'] = ssl._create_unverified_context()
            return old_urlopen(*args, **kwargs)
        urllib.request.urlopen = urlopen_no_ssl_verify
        old_requests_get = requests.get
        def requests_get_no_ssl_verify(*args, **kwargs):
            kwargs['verify'] = False
            return old_requests_get(*args, **kwargs)
        requests.get = requests_get_no_ssl_verify

        weasyprint.HTML(string=html_content, base_url=base_url, url_fetcher=custom_url_fetcher).write_pdf(save_path)

        # Restore original functions
        urllib.request.urlopen = old_urlopen
        requests.get = old_requests_get

        print(f"Saved HTML-as-PDF: {save_path}")
        return True
    except Exception as e:
        print(f"Failed to convert HTML to PDF {save_path}: {e}")
        return False


def get_soup(url):
    """
    Fetch URL content and return BeautifulSoup object.
    """
    try:
        with requests.get(url, timeout=30, verify=False) as resp:
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return None


def scrape_nic_eproc(base_url, site_name):
    """
    Generic NIC e-Procurement scraper:
    - Handles listing pages and downloads tender documents.
    """
    site_log = {
        "site": site_name,
        "url": base_url,
        "tenders_found": 0,
        "downloaded": 0,
        "failed": 0,
        "details": [],
    }
    seen_links = set()
    page_url = base_url

    while page_url:
        soup = get_soup(page_url)
        if not soup:
            break

        rows = soup.find_all("tr")
        for row in rows:
            links = row.find_all("a", href=True)
            for link in links:
                href = link["href"]
                text = link.get_text().strip() or link.get("title", "").strip()
                if not href or href.startswith("#") or "javascript" in href.lower():
                    continue
                full_link = urljoin(base_url, href)
                if full_link in seen_links:
                    continue
                seen_links.add(full_link)

                lower_href = href.lower()
                save_path = None
                # Download PDF, DOC, DOCX, or HTML files
                if any(
                    lower_href.endswith(ext)
                    for ext in [".pdf", ".doc", ".docx", ".html", ".htm"]
                ):
                    file_name = os.path.basename(href) or (
                        slugify(text)[:50] + os.path.splitext(href)[-1]
                    )
                    save_path = os.path.join(RAW_DIR, site_name, file_name)
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    success = download_file(full_link, save_path)
                    site_log["tenders_found"] += 1
                    if success:
                        site_log["downloaded"] += 1
                        site_log["details"].append(
                            {"link": full_link, "file": save_path, "status": "downloaded"}
                        )
                    else:
                        site_log["failed"] += 1
                        site_log["details"].append(
                            {"link": full_link, "file": save_path, "status": "failed"}
                        )

        # Check for pagination (looking for 'Next' link)
        next_link = soup.find("a", string=re.compile(r"Next|>"))
        if next_link and next_link.get("href"):
            page_url = urljoin(base_url, next_link["href"])
        else:
            break

    tender_log[site_name] = site_log


def scrape_nprocure(base_url, site_name):
    """
    Scraper for sites using the nProcure platform.
    """
    site_log = {
        "site": site_name,
        "url": base_url,
        "tenders_found": 0,
        "downloaded": 0,
        "failed": 0,
    }
    soup = get_soup(base_url)
    if not soup:
        tender_log[site_name] = site_log
        return

    rows = soup.select("table tr")
    for row in rows:
        link = row.find("a", href=True)
        if not link:
            continue
        href = link["href"]
        text = link.get_text().strip()
        full_link = urljoin(base_url, href)
        lower_href = href.lower()
        if any(
            lower_href.endswith(ext)
            for ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx"]
        ):
            file_name = os.path.basename(href) or slugify(text)[:50]
            save_path = os.path.join(RAW_DIR, site_name, file_name)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            success = download_file(full_link, save_path)
        else:
            tender_page = get_soup(full_link)
            if tender_page:
                html_content = str(tender_page)
                file_name = (
                    slugify(text)[:50] or f"tender_{site_log['tenders_found']+1}"
                )
                save_path = os.path.join(RAW_DIR, site_name, file_name + ".pdf")
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                success = convert_html_to_pdf(
                    html_content, save_path, base_url=full_link
                )
            else:
                success = False

        site_log["tenders_found"] += 1
        if success:
            site_log["downloaded"] += 1
        else:
            site_log["failed"] += 1

    tender_log[site_name] = site_log


def scrape_seci(site_url):
    """
    Scraper for Solar Energy Corporation of India (SECI).
    Assumes tender documents are linked directly as PDFs on their site.
    """
    site_name = "SECI Tenders"
    site_log = {
        "site": site_name,
        "url": site_url,
        "tenders_found": 0,
        "downloaded": 0,
        "failed": 0,
    }
    soup = get_soup(site_url)
    if not soup:
        tender_log[site_name] = site_log
        return

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.lower().endswith(".pdf"):
            full_link = urljoin(site_url, href)
            file_name = os.path.basename(href)
            save_path = os.path.join(RAW_DIR, site_name, file_name)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            success = download_file(full_link, save_path)
            site_log["tenders_found"] += 1
            if success:
                site_log["downloaded"] += 1
            else:
                site_log["failed"] += 1

    tender_log[site_name] = site_log


def main():
    tasks = [
        (scrape_nic_eproc, "https://pudutenders.gov.in", "Puducherry eProc"),
        (scrape_nic_eproc, "https://assamtenders.gov.in", "Assam eProc"),
        (scrape_nic_eproc, "https://eprocurebel.co.in", "Bharat Electronics Limited"),
        (scrape_nic_eproc, "https://jharkhandtenders.gov.in", "Jharkhand eProc"),
        (scrape_nic_eproc, "https://eproc.punjab.gov.in", "Punjab eProc"),
        (scrape_nic_eproc, "https://tenders.ladakh.gov.in", "Ladakh eProc"),
        (scrape_nic_eproc, "https://etender.up.nic.in", "Uttar Pradesh eProc"),
        (scrape_nic_eproc, "https://eprocurentpc.nic.in", "NTPC eProc"),
        (scrape_nic_eproc, "https://sikkimtender.gov.in", "Sikkim eProc"),
        (scrape_nic_eproc, "https://coalindiatenders.nic.in", "Coal India eProc"),
        (scrape_nic_eproc, "https://etenders.chd.nic.in", "Chandigarh eProc"),
        (scrape_nic_eproc, "https://tender.nprocure.com", "Gujarat eProc"),
        (scrape_nic_eproc, "https://arunachaltenders.gov.in", "Arunachal eProc"),
        (scrape_nic_eproc, "https://tendersutl.gov.in", "Uttarakhand eProc"),
        (scrape_nic_eproc, "https://etenders.hry.nic.in", "Haryana eProc"),
        (scrape_nic_eproc, "https://eproc2.bihar.gov.in", "Bihar eProc"),
        (scrape_nic_eproc, "https://cpcletenders.nic.in", "CPCLE Tenders"),
        (scrape_nic_eproc, "https://meghalayatenders.gov.in", "Meghalaya eProc"),
        (scrape_nic_eproc, "https://dnhtenders.gov.in", "Dadra & Nagar Haveli eProc"),
        (scrape_nic_eproc, "https://eprocurebhel.co.in", "BHEL eProc"),
        (scrape_nic_eproc, "https://defproc.gov.in", "Defence eProc"),
        (scrape_nic_eproc, "https://govtprocurement.delhi.gov.in", "Delhi eProc"),
        (scrape_nic_eproc, "https://eprocure.gov.in", "Government of India eProc"),
        (scrape_seci, "https://www.seci.co.in/"),
        (scrape_nic_eproc, "https://tender.telangana.gov.in", "Telangana eProc"),
        (
            scrape_nic_eproc,
            "https://tender.apeprocurement.gov.in",
            "Andhra Pradesh eProc",
        ),
        (
            scrape_nic_eproc,
            "https://eproc2.bihar.gov.in/EPSV2Web",
            "Bihar eProc (EPSV2)",
        ),
    ]

    for task in tasks:
        func = task[0]
        url = task[1]
        name = task[2] if len(task) > 2 else None
        try:
            if name:
                func(url, name)
            else:
                func(url)
            time.sleep(0.1)  # Add a small delay to avoid too many open files
        except Exception as e:
            print(f"Error in scraper for {name or url}: {e}")

    # Write the tender log data to JSON file
    with open("tender_log.json", "w") as log_file:
        json.dump(tender_log, log_file, indent=2, default=str)


def is_login_or_payment_required(soup):
    """
    Heuristic checks to detect if login or payment is required on the page.
    Returns True if login/payment required, else False.
    """
    if not soup:
        return True
    text = soup.get_text(separator=" ").lower()
    login_keywords = ["login", "sign in", "sign-in", "sign_in", "authentication", "password", "user id", "user name"]
    payment_keywords = ["payment", "pay now", "purchase", "buy", "subscribe", "credit card", "card number", "invoice"]
    for kw in login_keywords:
        if kw in text:
            return True
    for kw in payment_keywords:
        if kw in text:
            return True
    return False


def crawl_and_scrape_tenders(base_url, site_name, max_depth=2):
    """
    Generic scraper that crawls the website starting from base_url up to max_depth levels,
    looks for tender document links, checks for login/payment requirements,
    downloads or converts HTML tenders to PDF, and logs results.
    """
    site_log = {
        "site": site_name,
        "url": base_url,
        "tenders_found": 0,
        "downloaded": 0,
        "failed": 0,
        "login_or_payment_blocked": 0,
        "details": [],
    }
    seen_urls = set()
    to_crawl = [(base_url, 0)]
    domain = urlparse(base_url).netloc

    while to_crawl:
        current_url, depth = to_crawl.pop(0)
        if current_url in seen_urls or depth > max_depth:
            continue
        seen_urls.add(current_url)

        soup = get_soup(current_url)
        if not soup:
            site_log["failed"] += 1
            site_log["details"].append({"link": current_url, "status": "failed to fetch"})
            continue

        if is_login_or_payment_required(soup):
            site_log["login_or_payment_blocked"] += 1
            site_log["details"].append({"link": current_url, "status": "login/payment required"})
            continue

        # Find all links on the page
        links = soup.find_all("a", href=True)
        for link in links:
            href = link["href"]
            if href.startswith("#") or "javascript" in href.lower():
                continue
            full_link = urljoin(current_url, href)
            parsed_link = urlparse(full_link)
            # Only crawl links within the same domain
            if parsed_link.netloc != domain:
                continue

            lower_href = href.lower()
            if any(lower_href.endswith(ext) for ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip"]):
                # Direct file link
                file_name = os.path.basename(parsed_link.path) or slugify(link.get_text()[:50])
                save_path = os.path.join(RAW_DIR, site_name, file_name)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                success = download_file(full_link, save_path)
                site_log["tenders_found"] += 1
                if success:
                    site_log["downloaded"] += 1
                    site_log["details"].append({"link": full_link, "file": save_path, "status": "downloaded"})
                else:
                    site_log["failed"] += 1
                    site_log["details"].append({"link": full_link, "file": save_path, "status": "failed"})
            else:
                # HTML tender page, add to crawl queue if depth allows
                if full_link not in seen_urls and depth + 1 <= max_depth:
                    to_crawl.append((full_link, depth + 1))

        # Also consider converting current page if it looks like a tender page (heuristic)
        page_text = soup.get_text().lower()
        tender_keywords = ["tender", "bid", "quotation", "rfp", "request for proposal", "eproc", "e-procurement"]
        if any(kw in page_text for kw in tender_keywords):
            file_name = slugify(site_name) + f"_page_{depth}.pdf"
            save_path = os.path.join(RAW_DIR, site_name, file_name)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            success = convert_html_to_pdf(str(soup), save_path, base_url=current_url)
            site_log["tenders_found"] += 1
            if success:
                site_log["downloaded"] += 1
                site_log["details"].append({"link": current_url, "file": save_path, "status": "downloaded"})
            else:
                site_log["failed"] += 1
                site_log["details"].append({"link": current_url, "file": save_path, "status": "failed"})

    tender_log[site_name] = site_log


if __name__ == "__main__":
    main()
