# LinkedIn Job Crawler (Selenium → Google Sheets)

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Selenium](https://img.shields.io/badge/Selenium-Automation-green) ![Google%20Sheets](https://img.shields.io/badge/Google%20Sheets-API-success) ![Status](https://img.shields.io/badge/Status-Active-brightgreen)

> **Short description:**  
> Python-based LinkedIn job scraper using Selenium. Filters & dedupes results, skips non-English roles, and exports structured data to Google Sheets with resume-from-progress logging.

---

## ✨ What this project shows
- Browser automation with **Selenium** (Chrome, headless) and resilient waits.  
- **Login flow** with session bootstrapping + optional cookie restore.  
- **Rate-limit friendly** humanized delays and robust, CSS/XPath-based extraction.  
- **Language filtering** (skip non-EN) via `langdetect`.  
- **De-duplication** against existing sheet rows (Title+Company).  
- **Google Sheets** write-through with service accounts.  
- **Checkpointing** to `progress.log` so long runs can resume later.

---

## 🧭 How it works 
1. **Login** to LinkedIn using Selenium (`setup_driver_with_login()`), optionally headless.  
2. Build search URLs from flags (role/department/time/remote/location).  
3. Iterate cards, **skip “viewed”** items, and **language-filter** via `langdetect`.  
4. Extract fields (title, company, location, apply type, seniority hints, posted time, applicants, etc.). Data written to Google Sheets
5. **Deduplicate** vs existing sheet rows (Title+Company) and append new rows.  
6. Persist progress to `progress.log` so you can **resume** later from the right page.

---
## Filters Supported

| Filter             | Values / Description                               |
|--------------------|----------------------------------------------------|
| **Date Posted**     | Any time, Past 24h, Past Week, Past Month          |
| **Experience Level**| Internship, Entry level, Associate, Mid, Senior, Director|
| **Job Type**        | Full-time, Part-time, Contract, Temporary          |
| **Remote**          | On-site, Hybrid, Remote                            |
| **Location**        | Any country, city, or region                       |
| **Keyword**         | Free-text (e.g., "CRM", "Salesforce")              |
| **Easy Apply**      | Whether "Easy Apply" is enabled                    |

---

## 🛠️ Setup


1. Install dependencies:
```
pip install -r requirements.txt
```

2. Log into LinkedIn manually in Chrome.
3. Export cookies for `linkedin.com` using a browser extension.
4. Save cookies as `linkedin_cookies.json`.

5. Run script:
```python scrape_jobs.py
```
---

## 📦 Google Sheets integration logic
 
I use built-in **Google Sheets formulas** to automate cleanup and prioritization:

- **Applied check:** a `FILTER` or `COUNTIF` formula flags whether I’ve already applied — matching by *position name* and *company name*.  
- **Keyword sorting:** each tab filters jobs by topic (e.g. CRM, Growth, Product) using `REGEXMATCH(LOWER(A:A), "keyword")` to instantly surface new roles not yet found in previous runs.  
- **Status urgency:** jobs posted **less than 1 day ago** are marked with conditional formatting or `IF(REGEXMATCH(C2, "hour|minute"), "🔥 Urgent", "")`.  
- **Declined / excluded roles:** if I decide to skip a position, I just type `no` or any comment in the *Clean Data* tab — or the URL is auto-filtered out by a separate `FILTER` rule.  

This workflow is to keep the dataset continuously updated, actionable, and personalized without manual filtering.
---

## 🗂️ Project structure
```
.
├─ scrape_jobs.py        # main runner: batching, resume, parsing, Sheets I/O
├─ scraper.py            # driver setup + LinkedIn login (headless Chrome)
├─ limits_keywords.txt   # batch inputs (LIMIT|KEYWORDS|pos|dept)
├─ progress.log          # resume checkpoints
├─ credentials.json      # Google Service Account key
└─ README.md
```

---

## 🧪 Portfolio highlights
- Robust **DOM targeting** + **explicit waits** for dynamic pages.  
- **State management** for long scrapes (resume without re-scraping).  
- **Data hygiene**: language gates, duplicate prevention, structured exports.  
- Integration with a **third-party API** (Sheets) via service accounts.

---

## ⚖️ Legal & ethical note
This project is **for educational and personal use**. Respect target sites’ **Terms of Service** and robots policies, only scrape data you’re allowed to access, avoid high request rates. You are responsible for your usage.
