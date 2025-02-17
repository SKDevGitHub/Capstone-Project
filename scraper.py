import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

def get_driver_linux(): # "works on my machine" - Eliot K
    chrome_options = Options()
    chrome_options.binary_location = "/usr/bin/chromium"  # Adjust if needed
    chrome_options.add_argument("--headless")  # Run in headless mode (no UI)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    service = Service("/usr/bin/chromedriver")  # Adjust if needed
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

with get_driver_linux() as driver:
    driver.get("https://twitter.com/scrapingdog")
    time.sleep(5)
    with open("daytah","w+") as datafile:
        datafile.writelines(driver.page_source)
