import os
import json
import csv
import asyncio
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, User, PeerChannel
from telethon.errors import FloodWaitError, RPCError
import aiohttp
import sys
import shutil  # Import shutil for directory removal

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
                    'scrape_media': True,
                }
    return {
        'api_id': None,
        'api_hash': None,
        'phone': None,
        'channels': {},
        'scrape_media': True,
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
        'media_type': message.media.__class__.__name__ if message.media else None,
        'media_path': None,
        'reply_to': message.reply_to_msg_id if message.reply_to else None
    }

    channel_messages[channel].append(message_data)

MAX_RETRIES = 5

def clean_channel_id(channel):
    """Convert channel URL to a clean channel ID suitable for filenames"""
    if channel.startswith('https://t.me/'):
        return channel.split('/')[-1]  # Extract the username part
    return channel

async def download_media(channel, message, message_data):
    if not message.media or not state['scrape_media']:
        return None

    channel_dir = os.path.join(os.getcwd(), channel)
    media_folder = os.path.join(channel_dir, 'media')
    os.makedirs(media_folder, exist_ok=True)
    media_file_name = None
    if isinstance(message.media, MessageMediaPhoto):
        media_file_name = f"photo_{message.id}.jpg"
    elif isinstance(message.media, MessageMediaDocument):
        # Get original filename if available, otherwise create a generic one
        original_name = getattr(message.file, 'name', None)
        if original_name:
            # Remove any path components that might be in the filename
            media_file_name = os.path.basename(original_name)
        else:
            ext = getattr(message.file, 'ext', 'bin') or 'bin'
            media_file_name = f"doc_{message.id}.{ext}"
    else:
        print(f"Unsupported media type for message {message.id}. Skipping download.")
        return None

    # Ensure the filename is safe for Windows
    media_file_name = media_file_name.replace(':', '_').replace('/', '_').replace('\\', '_')
    media_path = os.path.join(media_folder, media_file_name)

    if os.path.exists(media_path):
        print(f"Media file already exists: {media_path}")
        message_data['media_path'] = media_path
        return media_path

    retries = 0
    while retries < MAX_RETRIES:
        try:
            # Download to the specific path we created
            media_path = await message.download_media(file=media_path)
            if media_path:
                print(f"Successfully downloaded media to: {media_path}")
                message_data['media_path'] = media_path
            break
        except (TimeoutError, aiohttp.ClientError, RPCError) as e:
            retries += 1
            print(f"Retrying download for message {message.id}. Attempt {retries}...")
            await asyncio.sleep(2 ** retries)
        except Exception as e:
            print(f"Error downloading media for message {message.id}: {str(e)}")
            return None
    return media_path

is_scraping_active = False
current_scraping_channel = None
scraping_start_time = None

async def scrape_channel(channel, offset_id):
    global is_scraping_active, current_scraping_channel, scraping_start_time

    try:
        # Set global flags to indicate scraping is active
        is_scraping_active = True
        current_scraping_channel = channel
        scraping_start_time = asyncio.get_event_loop().time()

        # Store the original channel identifier
        original_channel = channel

        # Clean the channel ID for file operations
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

        async for message in client.iter_messages(entity, offset_id=offset_id, reverse=True):
            total_messages += 1

        if total_messages == 0:
            print(f"No messages found in channel {channel}.")
            return

        last_message_id = None
        processed_messages = 0

        # Clear previous messages for this channel
        if clean_channel in channel_messages:
            channel_messages[clean_channel] = []

        async for message in client.iter_messages(entity, offset_id=offset_id, reverse=True):
            try:
                sender = await message.get_sender()
                message_data = {
                    'message_id': message.id,
                    'date': message.date.strftime('%Y-%m-%d %H:%M:%S'),
                    'sender_id': message.sender_id,
                    'first_name': getattr(sender, 'first_name', None) if isinstance(sender, User) else None,
                    'last_name': getattr(sender, 'last_name', None) if isinstance(sender, User) else None,
                    'username': getattr(sender, 'username', None) if isinstance(sender, User) else None,
                    'message': message.message,
                    'media_type': message.media.__class__.__name__ if message.media else None,
                    'media_path': None,
                    'reply_to': message.reply_to_msg_id if message.reply_to else None
                }

                if clean_channel not in channel_messages:
                    channel_messages[clean_channel] = []

                if state['scrape_media'] and message.media:
                    media_path = await download_media(clean_channel, message, message_data)

                channel_messages[clean_channel].append(message_data)

                last_message_id = message.id
                processed_messages += 1

                progress = (processed_messages / total_messages) * 100
                sys.stdout.write(f"\rScraping channel: {channel} - Progress: {progress:.2f}%")
                sys.stdout.flush()

                state['channels'][original_channel] = last_message_id
                save_state(state)
            except Exception as e:
                print(f"Error processing message {message.id}: {e}")

        # Save to CSV after scraping is complete
        save_to_csv(clean_channel)
        save_to_json(clean_channel) #also save to json
        print(f"\nSaved data for channel {channel} to CSV and JSON files.")

        print()
    except ValueError as e:
        print(f"Error with channel {channel}: {e}")
    finally:
        # Reset flags when scraping is done
        is_scraping_active = False
        current_scraping_channel = None
        scraping_start_time = None
    return channel_messages.get(clean_channel, []) # return the messages

def save_to_csv(channel):
    if channel not in channel_messages or not channel_messages[channel]:
        print(f"No messages to save for channel {channel}")
        return

    channel_dir = os.path.join(os.getcwd(), channel)
    os.makedirs(channel_dir, exist_ok=True)
    csv_file = os.path.join(channel_dir, f'{channel}.csv')

    try:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            # Get field names from the first message
            fieldnames = channel_messages[channel][0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            # Write header
            writer.writeheader()

            # Write data
            for message in channel_messages[channel]:
                writer.writerow(message)

        print(f"Successfully saved {len(channel_messages[channel])} messages to {csv_file}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")
        print(f"Attempted path: {csv_file}")
def save_to_json(channel):
    if channel not in channel_messages or not channel_messages[channel]:
        print(f"No messages to save for channel {channel}")
        return

    channel_dir = os.path.join(os.getcwd(), channel)
    os.makedirs(channel_dir, exist_ok=True)
    json_file = os.path.join(channel_dir, f'{channel}.json')

    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(channel_messages[channel], f, ensure_ascii=False, indent=4)

        print(f"Successfully saved {len(channel_messages[channel])} messages to {json_file}")
    except Exception as e:
        print(f"Error saving to JSON: {e}")
        print(f"Attempted path: {json_file}")

async def main():
    await client.start()
    try:
        channel_input = input("Enter the channel ID/URL to scrape: ")
        offset_id = 0  # You can change this if you want to start from a specific message
        messages = await scrape_channel(channel_input, offset_id) #get messages

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

if __name__ == '__main__':
    asyncio.run(main())
