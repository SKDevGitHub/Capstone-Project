import os
import json
import csv
import asyncio
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, User, PeerChannel
from telethon.errors import FloodWaitError, RPCError
import aiohttp
import sys
import datetime
from telethon.tl.functions.messages import GetHistoryRequest
import pytz # Import pytz

STATE_FILE = 'state.json'

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("Error: state.json is corrupted.  Creating a new state file.")
                return {
                    'api_id': None,
                    'api_hash': None,
                    'phone': None,
                    'channels': {},
                    'scrape_media': False,
                }
    return {
        'api_id': None,
        'api_hash': None,
        'phone': None,
        'channels': {},
        'scrape_media': False,
    }

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Error saving state to {STATE_FILE}: {e}")

state = load_state()

if not state['api_id'] or not state['api_hash'] or not state['phone']:
    state['api_id'] = int(input("Enter your API ID: "))
    state['api_hash'] = input("Enter your API Hash: ")
    state['phone'] = input("Enter your phone number: ")
    save_state(state)

client = TelegramClient('session', state['api_id'], state['api_hash'])

# Dictionary to store messages for each channel
channel_messages = {}

def save_message_to_memory(channel, message, sender):
    if channel not in channel_messages:
        channel_messages[channel] = []

    message_data = {
        'message_id': message.id,
        'date': message.date.strftime('%Y-%m-%d %H:%M:%S'),
        'sender_id': message.sender_id,
        'first_name': getattr(sender, 'first_name', None) if isinstance(sender, User) else None,
        'last_name': getattr(sender, 'last_name', None) if isinstance(sender, User) else None,
        'username': getattr(sender, 'username', None) if isinstance(sender, User) else None,
        'message': message.message,
        'reply_to': message.reply_to_msg_id if message.reply_to else None,
    }

    channel_messages[channel].append(message_data)

MAX_RETRIES = 5

def clean_channel_id(channel):
    """Convert channel URL to a clean channel ID suitable for filenames"""
    if channel.startswith('https://t.me/'):
        return channel.split('/')[-1]
    return channel

async def scrape_channel(channel):
    global is_scraping_active, current_scraping_channel, scraping_start_time

    try:
        is_scraping_active = True
        current_scraping_channel = channel
        scraping_start_time = asyncio.get_event_loop().time()

        original_channel = channel
        clean_channel = clean_channel_id(channel)

        try:
            if channel.startswith('https://t.me/'):
                entity = await client.get_entity(channel)
            elif channel.startswith('-'):
                entity = await client.get_entity(PeerChannel(int(channel)))
            else:
                entity = await client.get_entity(channel)
        except ValueError as e:
            print(f"Error with channel {channel}: {e}")
            return
        except Exception as e:
            print(f"Error getting entity for channel {channel}: {e}")
            return

        total_messages = 0
        processed_messages = 0
        last_message_id = None
        one_month_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30) # Make it offset-aware
        limit = 100

        if clean_channel in channel_messages:
            channel_messages[clean_channel] = []
        offset_id = 0
        while True:
            try:
                history = await client(
                    GetHistoryRequest(
                        peer=entity,
                        offset_id=offset_id,
                        offset_date=None,
                        add_offset=0,
                        limit=limit,
                        max_id=0,
                        min_id=0,
                        hash=0,
                    )
                )
            except FloodWaitError as e:
                print(f"FloodWaitError: {e.seconds} seconds")
                await asyncio.sleep(e.seconds)
                continue
            except Exception as e:
                print(f"Error fetching messages: {e}")
                break

            if not history.messages:
                break

            for message in history.messages:
                # Convert message.date to offset-aware if it's offset-naive
                if message.date.tzinfo is None or message.date.tzinfo.utcoffset(message.date) is None:
                    message_date_utc = message.date.replace(tzinfo=datetime.timezone.utc)
                else:
                    message_date_utc = message.date

                if message_date_utc < one_month_ago:
                    print(
                        f"Reached messages older than one month. Stopping scraping for channel {channel}."
                    )
                    break

                sender = await message.get_sender()
                message_data = {
                    "message_id": message.id,
                    "date": message_date_utc.strftime("%Y-%m-%d %H:%M:%S"),
                    "sender_id": message.sender_id,
                    "first_name": (
                        getattr(sender, "first_name", None)
                        if isinstance(sender, User)
                        else None
                    ),
                    "last_name": (
                        getattr(sender, "last_name", None)
                        if isinstance(sender, User)
                        else None
                    ),
                    "username": getattr(sender, "username", None)
                    if isinstance(sender, User)
                    else None,
                    "message": message.message,
                    "reply_to": message.reply_to_msg_id if message.reply_to else None,
                }

                if clean_channel not in channel_messages:
                    channel_messages[clean_channel] = []

                channel_messages[clean_channel].append(message_data)
                last_message_id = message.id
                processed_messages += 1
                total_messages += 1

                progress = (
                    100 if total_messages == 0 else (processed_messages / total_messages) * 100
                )
                sys.stdout.write(
                    f"\rScraping channel: {channel} - Progress: {progress:.2f}%"
                )
                sys.stdout.flush()
                offset_id = message.id
            if message_date_utc < one_month_ago:
                break
            if len(history.messages) < limit:
                break

        state["channels"][original_channel] = last_message_id
        save_state(state)

        save_to_csv(clean_channel)
        save_to_json(clean_channel)
        print(f"\nSaved data for channel {channel} to CSV and JSON files.")

        print()
    except ValueError as e:
        print(f"Error with channel {channel}: {e}")
    finally:
        is_scraping_active = False
        current_scraping_channel = None
        scraping_start_time = None
    return channel_messages.get(clean_channel, [])


def save_to_csv(channel):
    if channel not in channel_messages or not channel_messages[channel]:
        print(f"No messages to save for channel {channel}")
        return

    channel_dir = os.path.join(os.getcwd(), channel)
    os.makedirs(channel_dir, exist_ok=True)
    csv_file = os.path.join(channel_dir, f"{channel}.csv")

    try:
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            fieldnames = channel_messages[channel][0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for message in channel_messages[channel]:
                writer.writerow(message)

        print(
            f"Successfully saved {len(channel_messages[channel])} messages to {csv_file}"
        )
    except Exception as e:
        print(f"Error saving to CSV: {e}")
        print(f"Attempted path: {csv_file}")


def save_to_json(channel):
    if channel not in channel_messages or not channel_messages[channel]:
        print(f"No messages to save for channel {channel}")
        return

    channel_dir = os.path.join(os.getcwd(), channel)
    os.makedirs(channel_dir, exist_ok=True)
    json_file = os.path.join(channel_dir, f"{channel}.json")

    try:
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(channel_messages[channel], f, ensure_ascii=False, indent=4)

        print(
            f"Successfully saved {len(channel_messages[channel])} messages to {json_file}"
        )
    except Exception as e:
        print(f"Error saving to JSON: {e}")
        print(f"Attempted path: {json_file}")


async def main():
    await client.start()
    try:
        channel_input = input("Enter the channel ID/URL to scrape: ")
        messages = await scrape_channel(
            channel_input
        )

        if messages:
            print(f"Scraping and saving for channel '{channel_input}' complete.")
        else:
            print(f"No messages were scraped for channel '{channel_input}'.")

    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
