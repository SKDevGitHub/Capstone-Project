from telethon.sync import TelegramClient
from telethon import functions, types
from telethon import errors
import datetime
import time
import asyncio
import random

channels_2_join = set()
blacklist = set()

filename_from_stdin = input("input filename with telegram channels. or DONE: ")
while filename_from_stdin != "DONE":
    for line in open(filename_from_stdin,"r").readlines():
        channels_2_join.add(line.replace("\n",''))
    filename_from_stdin = input('input filename with telegram channels. or DONE: ')

filename_from_stdin = input("input blacklist file. or DONE: ")
while filename_from_stdin != "DONE":
    for line in open(filename_from_stdin,"r").readlines():
        blacklist.add(line.replace("\n",''))
    filename_from_stdin = input('input blacklist file. or DONE: ')

channels_2_join = channels_2_join.difference(blacklist)

api_id = ***REMOVED***
api_hash = ***REMOVED***

rate_limit_seconds = 30.0  # Start higher
min_rate_limit     = 10.0  # Never go below 10s

async def join_channels():
    global rate_limit_seconds
    async with TelegramClient("joiner", api_id, api_hash) as client:
        print("Successfully connected client")

        dialogs = await client(functions.messages.GetDialogsRequest(
            offset_date=None,
            offset_id=0,
            offset_peer=0,
            limit=500,
            hash=0
        ))

        already_joined = {chan.username for chan in dialogs.chats if chan.username}
        already_joined_count = len(already_joined)
        print(f"Already in {already_joined_count} channels")

        prospective_channels = channels_2_join.difference(already_joined)
        print(f"Found {len(prospective_channels)} new channels to join")

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
            
            except Exception as e:
                print(f"Unexpected error: {e}")
                break  # Stop on unknown errors

            # **Add random jitter to avoid bot-like patterns**
            sleep_time = rate_limit_seconds + random.uniform(0, 2)
            print(f"Sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)

asyncio.run(join_channels())