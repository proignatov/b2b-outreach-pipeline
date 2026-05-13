#!/usr/bin/env python3
"""
LLM Enrichment Layer — SDR intelligence on top of raw scraping data.

Pipeline:
  scraper.py → outreach.csv → enrich.py → outreach_enriched.csv

Adds:
  - lpr_title  : most likely decision maker role (no invented names)
  - lpr_email  : role-specific email pattern (or real found email)
  - outreach_angle : product category in B2B sales chain
  - personalization: SDR insight — what this product does + why it's relevant for outbound

Dependencies: pip install anthropic
Requires: ANTHROPIC_API_KEY in environment
"""

import csv
import os
import time

import anthropic

# Business model classification → most likely LPR role
LPR_ROLE_MAP = {
    "sales automation / CRM":              "Head of Sales",
    "marketing automation / CDP":          "Head of Marketing",
    "marketing automation / lead nurturing":"Head of Marketing / Growth",
    "email marketing automation":          "Head of Marketing",
    "email / SMS bulk sending":            "Head of Marketing",
    "marketing analytics / attribution":   "Head of Marketing / Growth",
    "marketing analytics / call tracking": "Head of Marketing",
    "ad budget optimization":              "Head of Marketing / Growth",
    "business telephony / communications": "Head of Sales",
    "cloud PBX / telephony":               "Head of IT / CTO",
    "live chat / sales communications":    "Head of Sales",
    "omnichannel chat platform":           "Head of CX / Sales",
    "messenger aggregator / customer comms":"Head of CX / Sales",
    "digital communications platform":    "Head of Marketing / CX",
    "HR tech / recruiting automation":     "Head of HR / CHRO",
    "HR tech / recruiting CRM":            "Head of HR",
    "HR document management":              "Head of HR",
    "HR tech / talent management":         "Head of HR / Talent Acquisition",
    "customer data quality / DQ":          "Head of Data / CTO",
    "data enrichment / address validation":"Head of Data / CTO",
    "regulatory compliance / accounting":  "CEO / CFO",
    "accounting outsourcing":              "CEO / CFO",
    "financial management / cash flow":    "CEO / CFO",
    "payment processing":                  "Head of Product / COO",
    "task management / BPM":               "Head of Operations / COO",
    "project management":                  "Head of Operations / COO",
    "AI project management":               "Head of Operations / COO",
    "enterprise low-code / BPM":           "COO / Head of Digital",
    "enterprise process automation":       "COO / Head of IT",
    "enterprise BPM / contact center":     "COO / Head of Operations",
    "enterprise ERP / document management":"COO / CFO",
    "customer support helpdesk":           "Head of Customer Support",
    "AI customer support":                 "Head of Customer Support",
    "online education platform":           "CEO / Head of Product",
    "online education / webinars":         "CEO / Head of Product",
    "service business automation":         "CEO / Operations Director",
    "event ticketing platform":            "CEO / Head of Operations",
    "DLP / employee monitoring":           "CISO / Head of Security",
    "information security / DLP":          "CISO / Head of Security",
    "AI brand visibility monitoring":      "Head of Marketing / CMO",
    "B2B procurement marketplace":         "Head of Procurement / COO",
}

# Role → most likely email prefix
LPR_EMAIL_PREFIX = {
    "Head of Sales":             "sales",
    "Head of Marketing":         "marketing",
    "Head of Marketing / Growth":"marketing",
    "Head of Marketing / CX":   "marketing",
    "Head of Marketing / CMO":  "marketing",
    "Head of HR / CHRO":         "hr",
    "Head of HR":                "hr",
    "Head of HR / Talent Acquisition": "hr",
    "Head of HR / CHRO":         "hr",
    "CEO / CFO":                 "info",
    "CEO / Head of Product":     "info",
    "CEO / Operations Director": "info",
    "CEO / Head of Operations":  "info",
    "Head of Operations / COO":  "info",
    "COO / Head of Digital":     "info",
    "COO / Head of IT":          "info",
    "COO / CFO":                 "info",
    "Head of Product / COO":     "info",
    "Head of Data / CTO":        "dev",
    "Head of IT / CTO":          "dev",
    "Head of CX / Sales":        "support",
    "Head of Customer Support":  "support",
    "CISO / Head of Security":   "security",
    "Head of Procurement / COO": "info",
}

OUTREACH_ANGLE = {
    "amocrm.ru":       "sales automation / CRM",
    "bitrix24.ru":     "sales automation / CRM",
    "retailcrm.ru":    "sales automation / CRM",
    "planfix.ru":      "sales automation / CRM",
    "kommo.com":       "sales automation / CRM",
    "mindbox.ru":      "marketing automation / CDP",
    "carrotquest.io":  "marketing automation / lead nurturing",
    "unisender.com":   "email marketing automation",
    "sendpulse.com":   "email marketing automation",
    "dashamail.ru":    "email marketing automation",
    "epochta.ru":      "email / SMS bulk sending",
    "expertsender.ru": "email marketing automation",
    "roistat.com":     "marketing analytics / attribution",
    "calltouch.ru":    "marketing analytics / attribution",
    "comagic.ru":      "marketing analytics / call tracking",
    "getuniq.me":      "ad budget optimization",
    "mango-office.ru": "business telephony / communications",
    "zadarma.com":     "cloud PBX / telephony",
    "jivosite.com":    "live chat / sales communications",
    "livetex.ru":      "omnichannel chat platform",
    "chat2desk.com":   "messenger aggregator / customer comms",
    "edna.ru":         "digital communications platform",
    "huntflow.ru":     "HR tech / recruiting automation",
    "talantix.ru":     "HR tech / recruiting CRM",
    "hrlink.ru":       "HR document management",
    "potok.io":        "HR tech / talent management",
    "hflabs.ru":       "customer data quality / DQ",
    "kontur.ru":       "regulatory compliance / accounting",
    "moedelo.org":     "accounting outsourcing",
    "dadata.ru":       "data enrichment / address validation",
    "finolog.ru":      "financial management / cash flow",
    "cloudpayments.ru":"payment processing",
    "robokassa.ru":    "payment processing",
    "pyrus.com":       "task management / BPM",
    "weeek.net":       "project management",
    "shtab.app":       "AI project management",
    "elma365.com":     "enterprise low-code / BPM",
    "directum.ru":     "enterprise process automation",
    "naumen.ru":       "enterprise BPM / contact center",
    "sbis.ru":         "enterprise ERP / document management",
    "omnidesk.ru":     "customer support helpdesk",
    "usedesk.ru":      "AI customer support",
    "getcourse.ru":    "online education platform",
    "bizon365.ru":     "online education / webinars",
    "yclients.com":    "service business automation",
    "qtickets.ru":     "event ticketing platform",
    "staffcop.ru":     "DLP / employee monitoring",
    "searchinform.ru": "information security / DLP",
    "signum.ai":       "AI brand visibility monitoring",
    "b2b-center.ru":   "B2B procurement marketplace",
}

TRANSFORM_PROMPT = """\
You are a B2B SDR. Rewrite as a 1-sentence outbound intelligence insight.

Company: {company}
Product type: {angle}
Decision maker: {lpr_title}
Raw description: {raw}

Rules:
- 1 sentence, max 140 characters
- Format: "[product focus], relevance for {lpr_title} — [why outbound makes sense]"
- No marketing language. No fluff. No copied sentences from the description.
- Language: Russian

Return only the insight text."""


def transform_personalization(
    client: anthropic.Anthropic, company: str, angle: str, lpr_title: str, raw: str
) -> str:
    if not raw or raw == company:
        return f"{angle.capitalize()} — потенциал для B2B outbound, особенно для {lpr_title}"

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=80,
        messages=[
            {
                "role": "user",
                "content": TRANSFORM_PROMPT.format(
                    company=company,
                    angle=angle,
                    lpr_title=lpr_title,
                    raw=raw[:400],
                ),
            }
        ],
    )
    return message.content[0].text.strip().strip('"').strip("'")


def get_lpr_email(real_email: str, lpr_title: str, domain: str) -> str:
    # Prefer a real found email (not info@ guess from scraper)
    if real_email and not real_email.startswith("info@"):
        return real_email
    prefix = LPR_EMAIL_PREFIX.get(lpr_title, "info")
    return f"{prefix}@{domain}"


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY not set. Run: export ANTHROPIC_API_KEY=sk-ant-...")

    client = anthropic.Anthropic(api_key=api_key)

    with open("outreach.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Dedup by domain
    seen = set()
    unique_rows = []
    for r in rows:
        if r["website"] not in seen:
            seen.add(r["website"])
            unique_rows.append(r)

    enriched = []
    for i, row in enumerate(unique_rows, 1):
        domain = row["website"]
        angle = OUTREACH_ANGLE.get(domain, "B2B SaaS platform")
        lpr_title = LPR_ROLE_MAP.get(angle, "CEO")
        lpr_email = get_lpr_email(row["email"], lpr_title, domain)

        print(f"[{i:02d}/{len(unique_rows)}] {domain} ...", end=" ", flush=True)
        sdr_insight = transform_personalization(
            client, row["company"], angle, lpr_title, row["personalization"]
        )

        enriched.append({
            "company":        row["company"],
            "website":        domain,
            "lpr_title":      lpr_title,
            "lpr_email":      lpr_email,
            "icp_score":      row["icp_score"],
            "outreach_angle": angle,
            "personalization":sdr_insight,
        })
        print("ok")
        time.sleep(0.3)

    fieldnames = ["company", "website", "lpr_title", "lpr_email", "icp_score",
                  "outreach_angle", "personalization"]
    with open("outreach_enriched.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched)

    lpr_found = sum(1 for r in enriched if not r["lpr_email"].startswith("info@"))
    scores = {str(s): sum(1 for r in enriched if r["icp_score"] == str(s)) for s in [1, 2, 3]}
    print(f"\nDone. {len(enriched)} rows → outreach_enriched.csv")
    print(f"ICP: 3={scores['3']}, 2={scores['2']}, 1={scores['1']}")
    print(f"LPR email (non-info@): {lpr_found}/{len(enriched)}")


if __name__ == "__main__":
    main()
