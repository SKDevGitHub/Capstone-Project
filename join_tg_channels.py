from telethon.sync import TelegramClient
from telethon import functions, types
from telethon import errors
import datetime
import time
import asyncio
import random

channels_2_join = set()
blacklist = set()

for line in open("tg_scraped_channels","r").readlines():
    channels_2_join.add(line.strip())

for line in open("blacklisted_tg_channels.dump","r").readlines():
    blacklist.add(line.strip())

channels_2_join = channels_2_join.difference(blacklist)

# USE YOUR OWN LOCAL VERSION OF api_id.secret AND NEVER ADD IT TO ANY FILE THAT ENDS UP ON GITHUB
api_id = open('api_id.secret','r').readlines()[0].strip()
# USE YOUR OWN LOCAL VERSION OF api_hash.secret AND NEVER ADD IT TO ANY FILE THAT ENDS UP ON GITHUB
api_hash = open('api_hash.secret','r').readlines()[0].strip()

rate_limit_seconds = 30.0  # Start higher
min_rate_limit     = 10.0  # Never go below 10s

async def join_channels():
    global rate_limit_seconds
    async with TelegramClient("joiner", api_id, api_hash) as client:
        print("Successfully connected client")

        # NOTE: this fails the first time you connect, but then works when you run the script again
        dialogs = await client(functions.messages.GetDialogsRequest(
            offset_date=None,
            offset_id=0,
            offset_peer=0,
            limit=500,
            hash=0
        ))

        already_joined = set()
        for chan in dialogs.chats:
            try:
                already_joined.add(chan.username)
            except:
                pass
        print(f"Already in {len(dialogs.chats)} channels")
        prospective_channels = channels_2_join.difference(already_joined)
        print(f"Found {len(prospective_channels)} new channels to join")
        already_joined_count = len(dialogs.chats)
        for channel in prospective_channels:
            if already_joined_count >= 499:  # Telegram limit
                print("Reached 500-channel limit. Stopping.")
                break

            try:
                if channel == "": continue
                print(f"Attempting to join channel {channel}")
                await client(functions.channels.JoinChannelRequest(channel=channel))
                already_joined_count += 1
                print(f"Joined channel {channel}, now in {already_joined_count} total")

                # **Gradually decrease rate limit but never below min**
                rate_limit_seconds = max(min_rate_limit, rate_limit_seconds - 0.1)
            
            except errors.FloodWaitError as e:
                print(f"FloodWaitError: Waiting {e.seconds} seconds")
                rate_limit_seconds = e.seconds + random.uniform(1, 3)  # Add jitter
                with open("last_flood_wait.impatient", "w") as file:
                    file.write(rate_limit_seconds)

            except Exception as e:
                print(f"Unexpected error: {e}")
                break  # Stop on unknown errors

            # **Add random jitter to avoid bot-like patterns**
            sleep_time = rate_limit_seconds + random.uniform(0, 2)
            print(f"Sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)

asyncio.run(join_channels())