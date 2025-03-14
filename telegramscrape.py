from telethon.sync import TelegramClient
from telethon import functions, types
import datetime

# Replace with your API ID and Hash
api_id = ***REMOVED***
api_hash = ***REMOVED***

with TelegramClient('scrape', api_id, api_hash) as client:
    result = client(functions.messages.SearchGlobalRequest(
        q='pump',
        filter=types.InputMessagesFilterPhotos(),
        min_date=datetime.datetime(2018, 6, 25),
        max_date=datetime.datetime(2025, 6, 25),
        offset_rate=0,
        offset_peer='username',
        offset_id=0,
        limit=100
    ))
    with open("outfile","w") as outfile:
        outfile.write(result.stringify())