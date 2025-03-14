import time
import re # reeeeeee
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

# keywords = ["pump","crypto","kucoin","solana","poloniex","signal"]
# keywords = ["degen","quant","wallstreet","token","whale"]
keywords = ["insider"]

channels = set()

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
    for keyword in keywords:
        print(f"scanning for keyword {keyword}")
        print(f"searching xtea")
        driver.get(f"https://xtea.pages.dev/search#gsc.tab=0&gsc.q={keyword}&gsc.sort=date")
        time.sleep(2)
        for match in re.findall('"https://t.me/s/[^"]*"',driver.page_source):
            channels.add(match)
        print(f"scanned result 1")

        for i in range(2,12):
            driver.get(f"https://xtea.pages.dev/search#gsc.tab=0&gsc.q={keyword}&gsc.sortdate=&gsc.page={i}")
            time.sleep(2)
            for match in re.findall('"https://t.me/s/[^"]*"',driver.page_source):
                channels.add(match)
            print(f"scanned result {i}")
        
        print(f"searching combot")
        driver.get(f"https://combot.org/top/telegram/groups?lng=all&page=1&q={keyword}")
        time.sleep(2)
        for match in re.findall('"https://t.me/s/[^"]*"',driver.page_source):
            channels.add(match)


channels2 = set()
for old in open("tgchans_search","r").readlines():
    channels2.add(old.replace("\n",''))

for chan in channels:
    new = chan.replace('"','')
    new = re.sub(r'\?.*','',new)
    new = re.sub(r'/[0-9]*$','',new)
    channels2.add(new)

with open("tgchans_search", "w") as tgchans:
    for channel in sorted(list(channels2)):
        tgchans.write(f"{channel}\n")