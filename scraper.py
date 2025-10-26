from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import os

EMAIL = "email@email.com"
PASSWORD = "password"

def setup_driver_with_login():
    options = Options()
    #options.add_argument("--start-maximized")
    options.add_argument("--headless") # run in background (no UI)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    driver.get("https://www.linkedin.com/login")
    time.sleep(3)

    driver.find_element(By.ID, "username").send_keys(EMAIL)
    time.sleep(1)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    time.sleep(1)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()

    time.sleep(5)
    return driver


#cookie option, turned off
#COOKIE_FILE = "linkedin_cookies.json"
def setup_driver_with_cookies():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://www.linkedin.com")

    # Загружаем cookies
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r") as f:
            cookies = json.load(f)
        for cookie in cookies:
            # Удалить поля, которые могут вызвать ошибки
            cookie.pop("sameSite", None)
            cookie.pop("storeId", None)
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"⚠️ Failed to add cookie: {e}")

        driver.refresh()
        time.sleep(3)
        print("✅ LinkedIn session restored using cookies.")
    else:
        print("⚠️ Cookie file not found! Log in manually and export cookies.")

    return driver