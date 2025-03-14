import time
import re # reeeeeee
import random
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

keywords = list()
for line in open("keywords","r").readlines():
    if line == "": continue
    else:
        without_newline = line.replace("\n","")
        keywords.append(without_newline)

channels_found = set()
with get_driver_linux() as driver:
    for keyword in keywords:
        print(f"scanning for keyword {keyword}")
        print(f"searching xtea")
        driver.get(f"https://xtea.pages.dev/search#gsc.tab=0&gsc.q={keyword}&gsc.sort=date")
        time.sleep(2 + random.uniform(1, 3)) # random jitter to avoid bot-like behavior
        for match in re.findall('"https://t.me/s/[^"]*"',driver.page_source):
            channels_found.add(match)
        print(f"scanned result 1")

        for i in range(2,12):
            driver.get(f"https://xtea.pages.dev/search#gsc.tab=0&gsc.q={keyword}&gsc.sortdate=&gsc.page={i}")
            time.sleep(2 + random.uniform(1, 3))
            for match in re.findall('"https://t.me/s/[^"]*"',driver.page_source):
                channels_found.add(match)
            print(f"scanned result {i}")
        
        print(f"searching combot")
        driver.get(f"https://combot.org/top/telegram/groups?lng=all&page=1&q={keyword}")
        time.sleep(2 + random.uniform(1, 3))
        for match in re.findall('"https://t.me/s/[^"]*"',driver.page_source):
            channels_found.add(match)

# add the channels found last time to the set, so we avoid repeats but keep data
for old in open("tg_scraped_channels","r").readlines():
    channels_found.add(old.replace("\n",''))

for chan in channels_found:
    new = chan.replace('"','')
    new = re.sub(r'\?.*','',new)
    new = re.sub(r'/[0-9]*$','',new)
    channels_found.add(new)

with open("tg_scraped_channels", "w") as tgchans:
    for channel in sorted(list(channels_found)):
        tgchans.write(f"{channel}\n")