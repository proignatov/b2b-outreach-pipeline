#!/usr/bin/env python3
"""
B2B Cold Email Outreach Scraper
INPUT:  domains.txt
OUTPUT: outreach.csv

Dependencies: pip install requests beautifulsoup4
"""

import csv
import re
import time
import warnings

import requests
import urllib3
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}
TIMEOUT = 10
SLEEP_BETWEEN = 1.0

# ICP score: 3=core buyer, 2=adjacent, 1=weak fit
ICP_SCORES = {
    # CRM / Sales tools — direct cold email buyers
    "amocrm.ru": 3, "bitrix24.ru": 3, "retailcrm.ru": 3, "planfix.ru": 3, "kommo.com": 3,
    # Marketing automation / Email platforms
    "mindbox.ru": 3, "carrotquest.io": 3, "unisender.com": 3, "sendpulse.com": 3,
    "dashamail.ru": 3, "epochta.ru": 3, "expertsender.ru": 3,
    # Analytics / Attribution
    "roistat.com": 3, "calltouch.ru": 3, "comagic.ru": 3, "getuniq.me": 3,
    # Telephony / Chat — B2B, active sales teams
    "mango-office.ru": 2, "zadarma.com": 2, "jivosite.com": 2, "livetex.ru": 2,
    "chat2desk.com": 2, "edna.ru": 2,
    # HR tech
    "huntflow.ru": 2, "talantix.ru": 2, "hrlink.ru": 2, "potok.io": 2, "hflabs.ru": 2,
    # Finance / Payments
    "finolog.ru": 2, "cloudpayments.ru": 2, "robokassa.ru": 2, "moedelo.org": 2, "dadata.ru": 2,
    # Project management / Collaboration
    "pyrus.com": 2, "weeek.net": 2, "shtab.app": 2,
    # Customer support
    "usedesk.ru": 2,
    # Booking / tickets
    "yclients.com": 2,
    # ERP / Government / Enterprise-first
    "elma365.com": 1, "directum.ru": 1, "naumen.ru": 1, "sbis.ru": 1, "kontur.ru": 1,
    # Help desk (smaller market)
    "omnidesk.ru": 1,
    # EdTech
    "getcourse.ru": 1, "bizon365.ru": 1,
    # Niche / ticketing
    "qtickets.ru": 1,
    # Security (DLP — different buyer, long sales cycle)
    "staffcop.ru": 1, "searchinform.ru": 1,
    # AI visibility / niche
    "signum.ai": 1,
    # B2B marketplace
    "b2b-center.ru": 1,
}


def fetch_html(domain: str) -> str | None:
    for scheme in ("https", "http"):
        try:
            resp = requests.get(
                f"{scheme}://{domain}",
                headers=HEADERS,
                timeout=TIMEOUT,
                verify=False,
                allow_redirects=True,
            )
            if resp.ok:
                # Trust the server's declared charset; only guess when it's absent
                resp.encoding = resp.encoding if "charset=" in resp.headers.get("content-type", "").lower() else resp.apparent_encoding
                return resp.text
        except Exception:
            continue
    return None


def first_clean_sentence(text: str, max_len: int = 130) -> str:
    """Extract first sentence that is at least 20 chars and under max_len."""
    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    for s in sentences:
        s = s.strip().rstrip(".")
        if len(s) >= 20:
            return s[:max_len]
    # Fallback: just truncate at word boundary
    short = text.strip()[:max_len]
    return short.rsplit(" ", 1)[0] if " " in short else short


def extract_data(domain: str, html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    # Company name: first segment of title
    raw_title = soup.title.string.strip() if soup.title else domain
    company = re.split(r"[|—\-–]", raw_title)[0].strip() or domain

    # Meta description (most reliable)
    meta_tag = soup.find("meta", attrs={"name": "description"})
    meta_desc = meta_tag.get("content", "").strip() if meta_tag else ""

    # First substantial paragraph (≥30 chars)
    intro = ""
    for p_tag in soup.find_all("p"):
        text = p_tag.get_text(" ", strip=True)
        if len(text) >= 30:
            intro = text
            break

    # Priority: meta description → intro → title
    source = meta_desc or intro or raw_title

    # Clean: extract first meaningful sentence
    personalization = first_clean_sentence(source)

    # Email: real mailto first, then guess
    mailto = soup.find("a", href=re.compile(r"^mailto:", re.I))
    if mailto:
        email = mailto["href"].replace("mailto:", "").split("?")[0].strip()
    else:
        email = f"info@{domain}"

    icp_score = ICP_SCORES.get(domain, 2)

    return {
        "company": company,
        "website": domain,
        "email": email,
        "icp_score": icp_score,
        "personalization": personalization,
    }


def make_fallback_row(domain: str) -> dict:
    return {
        "company": domain,
        "website": domain,
        "email": f"info@{domain}",
        "icp_score": ICP_SCORES.get(domain, 2),
        "personalization": f"{domain}",
    }


def main():
    with open("domains.txt", encoding="utf-8") as f:
        domains = [line.strip() for line in f if line.strip()]

    rows = []
    for i, domain in enumerate(domains, 1):
        print(f"[{i:02d}/{len(domains)}] {domain} ...", end=" ", flush=True)
        html = fetch_html(domain)
        if html:
            row = extract_data(domain, html)
            print("ok")
        else:
            row = make_fallback_row(domain)
            print("failed (fallback)")
        rows.append(row)
        time.sleep(SLEEP_BETWEEN)

    fieldnames = ["company", "website", "email", "icp_score", "personalization"]
    with open("outreach.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    scores = {3: 0, 2: 0, 1: 0}
    for r in rows:
        scores[r["icp_score"]] += 1
    print(f"\nDone. {len(rows)} rows → outreach.csv")
    print(f"ICP: score-3={scores[3]}, score-2={scores[2]}, score-1={scores[1]}")


if __name__ == "__main__":
    main()
