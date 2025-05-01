from telethon.sync import TelegramClient
from telethon.tl.types import Channel, Chat
from telethon.tl.functions.channels import LeaveChannelRequest, GetFullChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest
from telethon import errors
import datetime
import time
import asyncio
import random
from langdetect import detect, LangDetectException

# USE YOUR OWN LOCAL VERSION OF api_id.secret AND NEVER ADD IT TO ANY FILE THAT ENDS UP ON GITHUB
api_id = open('api_id.secret','r').readlines()[0].strip()
# USE YOUR OWN LOCAL VERSION OF api_hash.secret AND NEVER ADD IT TO ANY FILE THAT ENDS UP ON GITHUB
api_hash = open('api_hash.secret','r').readlines()[0].strip()

rate_limit_seconds = 30.0  # Start higher
min_rate_limit     = 10.0  # Never go below 10s

client = TelegramClient('session_name', api_id, api_hash)

async def should_leave_channel(channel):
    try:
        # Language check
        try:
            lang = detect(channel.title)
            if lang != 'en':
                print(f"Non-English title detected ({lang}): {channel.title}")
                return True
        except LangDetectException:
            print(f"Language detection failed: {channel.title}")
            return True

        # Get full channel details (for member count)
        full = await client(GetFullChannelRequest(channel))
        members = full.full_chat.participants_count

        if members < 500:
            return True
    
        # Get most recent message timestamp
        async for msg in client.iter_messages(channel, limit=1):
            if msg.date < datetime.utcnow() - datetime.timedelta(days=90):
                return True
            else:
                return False
        
        # If no messages found at all
        return True
    
    except (errors.ChatAdminRequiredError, errors.ChannelPrivateError, errors.UserPrivacyRestrictedError, errors.RPCError) as e:
        return True

    except Exception as e:
        return False

async def leave_channels():
    await client.start()

    dialogs = await client.get_dialogs()
    for dialog in dialogs:
        if isinstance(dialog.entity, Channel) and dialog.is_channel:
            channel = dialog.entity
            print(f'Checking: {channel.title}')
            if await should_leave_channel(channel):
                print(f'Leaving: {channel.title}')
                await client(LeaveChannelRequest(channel))

    await client.disconnect()

with client:
    client.loop.run_until_complete(leave_channels())