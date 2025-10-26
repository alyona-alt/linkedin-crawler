from scraper import setup_driver_with_login
from scraper import setup_driver_with_cookies
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from oauth2client.service_account import ServiceAccountCredentials
from langdetect import detect
import time
from datetime import datetime
import pytz
import random
import re
import gspread
import pandas as pd
import threading
import keyboard
import os, json

PROGRESS_LOG = "progress.log"

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("LinkedIn Jobs").sheet1 #search by file name

existing_rows = sheet.get_all_values()
existing_pairs = set(
    (row[1].strip().lower(), row[2].strip().lower())  # Title in column B, Company in column C
    for row in existing_rows[1:] if len(row) >= 3
)

LOCATION = "Germany"
EXPERIENCE = "" #"f_E=4&" #senior-mid #%2 -> &director 
TIME = "f_TPR=r604800&" #r86400 24h -> #r604800 1w -> r2592000 1m
REMOTE = "" # f_WT=3%2C2 also hybrid -> WT=3 hybrid 
POSITION = "f_T=1166%2C26%2C12641%2C1187%2C2327%2C70%2C12261%2C2673&"
DEPARTMENT = "f_F=mrkt%2Cbd%2Cmgmt%2Cprdm%2Cadvr&"

# ЗАПУСК БРАУЗЕРА
driver = setup_driver_with_login()
time.sleep(3)
print("🟢 Magic Ahead.")

cet = pytz.timezone("CET")
now = datetime.now(cet).strftime("%d/%m %H:%M:%S")

def human_sleep(base=1, variation=1, jitter=0.5):#3
    """Sleep for a human-like random duration"""
    sleep_time = base + random.uniform(0, variation) + random.gauss(0, jitter)
    sleep_time = max(0.5, sleep_time)  # don't go negative
    print(f"[INFO] Sleeping for {sleep_time:.2f} seconds...")
    time.sleep(sleep_time)


## helpers
def _log_key(limit, keywords, pos_flag, dept_flag):
    kw = (keywords or "").strip()
    return f"{limit}|{kw}|{pos_flag}|{dept_flag}"

def _read_progress():
    progress = {}
    if not os.path.exists(PROGRESS_LOG):
        return progress
    with open(PROGRESS_LOG, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) < 7:
                continue
            limit, kw, pos, dept, status, page = parts[:6]
            updated = parts[6] if len(parts) > 6 else ""
            key = _log_key(limit, kw, pos, dept)
            progress[key] = {
                "limit": int(limit),
                "keywords": kw,
                "pos": pos,
                "dept": dept,
                "status": status,       # "process" | "done"
                "page": int(page),      # start=
                "updated_at": updated
            }
    return progress

def _write_progress(progress: dict):
    with open(PROGRESS_LOG, "w", encoding="utf-8") as f:
        for key, rec in progress.items():
            line = "|".join([
                str(rec["limit"]),
                rec["keywords"],
                rec["pos"],
                rec["dept"],
                rec.get("status", "process"),
                str(rec.get("page", 0)),
                rec.get("updated_at", "")
            ])
            f.write(line + "\n")

def _set_progress_record(progress: dict, limit, keywords, pos, dept, status, page):
    tz = pytz.timezone("CET")
    key = _log_key(limit, keywords, pos, dept)
    progress[key] = {
        "limit": int(limit),
        "keywords": (keywords or "").strip(),
        "pos": str(pos),
        "dept": str(dept),
        "status": status,            # "process" | "done"
        "page": int(page),
        "updated_at": datetime.now(tz).isoformat()
    }

def log_update(limit, keywords, pos, dept, status, page):
    progress = _read_progress()
    _set_progress_record(progress, limit, keywords, pos, dept, status, page)
    _write_progress(progress)

## end of helpers.


# cycle for interactive parcing
def run_scraper(LIMIT, KEYWORDS, position_flag="1", department_flag="1", start_page=0, resume=False):
    last_ping = time.time()
    jobs = [] #будто бы не используем
    seen_links = set()
    total_jobs_scraped = 0

    #for page in range(0, LIMIT, 25): -> for option where limit < 25 doesn't work 
    for page in range(start_page, 2000, 25):  # limit is controlled by this line
        if total_jobs_scraped >= LIMIT:
            break

        #url = f"https://www.linkedin.com/jobs/search/?{DEPARTMENT}{REMOTE}{POSITION}{TIME}keywords={KEYWORDS}&location={LOCATION}&{EXPERIENCE}start={page}"
        pos = POSITION if str(position_flag) == "1" else ""
        dept = DEPARTMENT if str(department_flag) == "1" else ""
        url = f"https://www.linkedin.com/jobs/search/?{dept}{REMOTE}{pos}{TIME}keywords={KEYWORDS}&location={LOCATION}&{EXPERIENCE}start={page}"
        print(f"🌐 Opening page: {url}")
        try:
            driver.get(url) #there was just two lines without try logic. 
            human_sleep() #time.sleep(random.uniform(3, 6))  
            #time.sleep(5)
        except Exception as e:
            print(f"❌ Error when page is loading: {e}")
            print("🛑 Break run_scraper, going back to menu")
            return
        human_sleep()

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.scaffold-layout__list"))
        )

        job_cards = driver.find_elements(By.CSS_SELECTOR, "li.scaffold-layout__list-item")
        print(f"🔍 Found {len(job_cards)} job cards on page {page//25 + 1}")

        if not job_cards:
            print(f"❌ No positions available at the page {page}.")
            if resume:
                log_update(LIMIT, KEYWORDS, position_flag, department_flag, "process", page)
            break
            """choice = input("Продолжить парсинг дальше? (y/n): ").strip().lower()
                                                if choice != 'y':
                                                    print("🛑 Парсинг остановлен пользователем.")
                                                    break"""

        for i, card in enumerate(job_cards):
            viewed_flag = False
            try:
                viewed_elems = card.find_elements(By.CSS_SELECTOR, "li.job-card-container__footer-item.job-card-container__footer-job-state.t-bold")
                for v in viewed_elems:
                    if "viewed" in v.text.lower():
                        viewed_flag = True
                        break
            except Exception as e:
                print(f"⚠️ Error when check for status viewed: {e}")

            if viewed_flag:
                print(f"⏭ Miss the card #{i+1} — already viewed.")
                continue

            try:
                # Если не просмотрена — кликаем и продолжаем обработку
                card.click()
                total_jobs_scraped += 1
                time.sleep(random.uniform(0.7, 2.5))  # между карточками было пять. 1.5, 3.0 
                #time.sleep(3)

                # Job description text for language filtering & tag
                try:
                    description_elem = driver.find_element(By.CSS_SELECTOR, "div#job-details")
                    description_text = description_elem.text.strip()
                    tag = ""
                    error_count = 0
                    MAX_ERRORS = 10

                    language = detect(description_text)
                    if language != "en":
                        print(f"⏭ Skipping non-English job #{i+1} — Detected: {language}")
                        continue
                except Exception as e:
                    print(f"❌ Failed language detection for job #{i+1}: {e}")
                    #print(f"[DEBUG] description_text_o2:\n{description_text_o2[:500]}")
                    error_count += 1

                    if error_count >= MAX_ERRORS:
                            answer = input(f"\n⚠️ {error_count} errors encountered. Do you want to continue? (y/n): ").strip().lower()
                            if answer != 'y':
                                print("🛑 Script stopped by user after repeated errors.")
                                break
                    #pass continue
                # language filtering is over


                # Название + ссылка
                title_elem = driver.find_element(By.CSS_SELECTOR, "h1.t-24.t-bold.inline a")
                title = title_elem.text.strip()
                link = title_elem.get_attribute("href")
                #link = "https://www.linkedin.com" + title_elem.get_attribute("href")

                # проверка на дупликаты
                if link in seen_links:
                    print(f"🔁 Duplicate job skipped: {title}")
                    continue
                seen_links.add(link)
            except:
                title, link = "N/A", "N/A"
                continue

            company = ""
            company_link = ""
            location = ""
            prefix = ""
            apply_type = ""
            total_employees = ""
            last_comment = ""
            large_note = ""
            time_posted = ""
            applicants = ""

            too_late_flag = ""
            try:
                closed_elem = driver.find_element(By.XPATH, "//span[contains(text(), 'No longer accepting applications')]")
                #closed_elem = driver.find_element(By.CSS_SELECTOR, "div.jobs-details-top-card__apply-error")
                if "No longer accepting applications" in closed_elem.text:
                    too_late_flag = "too late"
            except:
                pass


            try:
                company_elem = driver.find_element(By.CSS_SELECTOR, "div.job-details-jobs-unified-top-card__company-name a")
                company = company_elem.text.strip()

                # title+company check 
                job_key = (title.strip().lower(), company.strip().lower())
                if job_key in existing_pairs:
                    print(f"🔁 Duplicate job skipped: {title} @ {company}")
                    continue


                company_link = company_elem.get_attribute("href").strip()
                total_employees = driver.find_element(By.CSS_SELECTOR, "li.jobs-premium-company-growth__stat-item p").text.strip()
                location = driver.find_element(By.CSS_SELECTOR, "div.job-details-jobs-unified-top-card__primary-description-container span.tvm__text.tvm__text--low-emphasis").text.strip()
                #prefix = driver.find_element(By.XPATH, "//button[.//strong[contains(text(),'Hybrid') or contains(text(),'Remote') or contains(text(),'On-site')]]").text.strip()
                prefix = driver.find_element(By.XPATH, "//button[.//strong[contains(text(),'Hybrid') or contains(text(),'Remote') or contains(text(),'On-site')]]").text.strip().split()[0]
                apply_type = driver.find_element(By.CSS_SELECTOR, "button.jobs-apply-button span.artdeco-button__text").text.strip()

                #note
                large_note = driver.find_element(By.CSS_SELECTOR, "div.job-details-jobs-unified-top-card__primary-description-container span").text.strip()
                low_emphasis_spans = driver.find_elements(By.CSS_SELECTOR, "div.job-details-jobs-unified-top-card__primary-description-container span.tvm__text.tvm__text--low-emphasis")
                
                #get the time 
                try:
                    raw_line = driver.find_element(By.CSS_SELECTOR, "div.job-details-jobs-unified-top-card__primary-description-container").text
                except:
                    raw_line = ""

                # Fallback to JS innerText if empty
                if not raw_line:
                    try:
                        raw_line = driver.execute_script("""
                            let el = document.querySelector('div.job-details-jobs-unified-top-card__primary-description-container');
                            return el ? el.innerText : '';
                        """).strip()
                    except:
                        raw_line = ""
                        #ended


                parts = [p.strip() for p in raw_line.split("·")]

                time_posted = next((p for p in parts if re.search(r"\b\d+\s+(minute|hour|day|week|month)s?\s+ago\b", p.lower())), "N/A")
                applicants = next((p for p in parts if re.search(r"(applicant|people clicked apply)", p.lower())), "N/A")
                last_comment = next((p for p in parts if re.search(r"(actively reviewing applicants|company review time|responses managed off linkedin|no response insights)", p.lower())), "N/A")

              
            except:
                pass

            sheet.append_row([now, link, title, company, company_link, location, prefix, apply_type, time_posted, applicants, tag, total_employees, last_comment, large_note, too_late_flag])
            print(f"✅ {total_jobs_scraped} out of {LIMIT}|{KEYWORDS}:  {title} | {company} | {location} | {link}")
            #print(f"✅ {i+1}. {title} | {company} | {location} | {link}")
            existing_pairs.add(job_key)
            time.sleep(2)

            if resume:
                log_update(LIMIT, KEYWORDS, position_flag, department_flag, "process", page + 25)

            #here to put new limit
            if total_jobs_scraped >= LIMIT:
                print(f"🔚 Reached job LIMIT ({LIMIT})")
                break

        if total_jobs_scraped >= LIMIT: #still for limit
            break

    if resume:
        log_update(LIMIT, KEYWORDS, position_flag, department_flag, "done", 0)



# magic is here
# 🔁 also recurring cycle 
try:
    while True:
        print("hello, choose me:")
        print("1 — all LIMIT + KEYWORDS from the file (do NOT READ progress.log, BUT write in it)")
        print("2 — manual input (do NOT WRITE in the progress.log)")
        print("3 — all LIMIT + KEYWORD. progress applied (CONTINUE from progress.log)")

        mode = input("🔧 your choice matters (1/2/3): ").strip()

        if mode == "1":
            # do NOT READ progress.log, BUT write in it
            try:
                with open("limits_keywords.txt", "r", encoding="utf-8") as f:
                    for raw in f:
                        line = raw.strip()
                        if not line or line.startswith("#"):
                            continue
                        parts = line.split("|")
                        limit    = parts[0].strip() if len(parts) > 0 else ""
                        keywords = parts[1].strip() if len(parts) > 1 else ""
                        pos_flag = parts[2].strip() if len(parts) > 2 else "1"
                        dept_flag= parts[3].strip() if len(parts) > 3 else "1"

                        try:
                            LIMIT = int(limit)
                        except ValueError:
                            print(f"⚠️ skip the line (LIMIT): {line}")
                            continue

                        print(f"\n🚀 NEW LAUNCH (write-only progress): LIMIT={LIMIT}, KEYWORDS={keywords!r}, POS={pos_flag}, DEPT={dept_flag}")
                        # отметим начало "process" c page=0 (опционально)
                        log_update(LIMIT, keywords, pos_flag, dept_flag, "process", 0)
                        # запускаем с нуля, но с resume=True, чтобы страница/finish писались в лог
                        run_scraper(LIMIT, keywords, pos_flag, dept_flag, start_page=0, resume=True)
            except FileNotFoundError:
                print("❌ file limits_keywords.txt is not found.")

        elif mode == "2":
            # manual launch
            LIMIT = int(input("🔢 Your Limit: ") or 10)
            KEYWORDS = input("🔍 Your Keywords: ") or ""
            pos_flag = input("pos_flag (1/0, Enter=1): ").strip() or "1"
            dept_flag = input("dept_flag (1/0, Enter=1): ").strip() or "1"
            run_scraper(LIMIT, KEYWORDS, pos_flag, dept_flag, start_page=0, resume=False)

        elif mode == "3":
            # read progress & continue from the page
            try:
                progress = _read_progress()
                with open("limits_keywords.txt", "r", encoding="utf-8") as f:
                    for raw in f:
                        line = raw.strip()
                        if not line or line.startswith("#"):
                            continue
                        parts = line.split("|")
                        limit    = parts[0].strip() if len(parts) > 0 else ""
                        keywords = parts[1].strip() if len(parts) > 1 else ""
                        pos_flag = parts[2].strip() if len(parts) > 2 else "1"
                        dept_flag= parts[3].strip() if len(parts) > 3 else "1"

                        try:
                            LIMIT = int(limit)
                        except ValueError:
                            print(f"⚠️ Пропуск строки (LIMIT не число): {line}")
                            continue

                        key = _log_key(limit, keywords, pos_flag, dept_flag)
                        rec = progress.get(key)

                        # если уже done — пропускаем
                        if rec and rec.get("status") == "done":
                            print(f"✔️ done already, skip: {limit}|{keywords}|{pos_flag}|{dept_flag}")
                            continue

                        start_page = int(rec.get("page", 0)) if rec else 0
                        print(f"\n↩️ Resume: LIMIT={LIMIT}, KEYWORDS={keywords!r}, POS={pos_flag}, DEPT={dept_flag}, start={start_page}")

                        log_update(LIMIT, keywords, pos_flag, dept_flag, "process", start_page)
                        run_scraper(LIMIT, keywords, pos_flag, dept_flag, start_page=start_page, resume=True)
            except FileNotFoundError:
                print("❌ file limits_keywords.txt is not found.")

        else:
            print("🤷 incorrect mode.")

        again = input("🔁 Wanna launch again? (y/n): ").strip().lower()
        if again != "y":
            break

except KeyboardInterrupt:
    print("\n🛑 Stopped by the user. Driver remains open.")


#driver.quit()
print("📁 Output saved to google sheet")

#df = pd.DataFrame(jobs)
#df.to_csv("output/linkedin_jobs.csv", index=False)
#print("📁 Output saved to: output/linkedin_jobs.csv")
