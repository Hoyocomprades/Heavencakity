import discord
from discord.ext import tasks
import asyncio
import os
import io
from collections import deque
from keep_alive import keep_alive  # Import the keep_alive function

# Load environment variable securely (assuming .env file exists)
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Channel IDs (replace with your actual channel IDs)
SOURCE_CHANNEL_IDS = [
    863803391239127090,
    1248563358995709962
    # Add more source channel IDs here as needed
]
DESTINATION_CHANNEL_IDS = [
    1248563406101942282,
    1248574132417724518,
    1248623054226067577
]

class ForwardingBot(discord.Client):

    def __init__(self):
        from discord import Intents
        intents = Intents.default()
        if hasattr(Intents, 'message_content'):
            intents.message_content = True  # For discord.py v2.0 and later
        else:
            intents = Intents.all()  # For earlier versions of discord.py
        
        super().__init__(intents=intents)
        self.last_message_ids = {channel_id: None for channel_id in SOURCE_CHANNEL_IDS}
        self.forwarded_messages = {}  # Dictionary to keep track of forwarded messages
        self.message_queue = deque()  # Queue to store incoming messages

    async def process_message(self, message):
        if message.attachments:
            content = message.content.strip() if message.content else ""
            attachment = message.attachments[0]
            file_content = await attachment.read()

            for destination_channel_id in DESTINATION_CHANNEL_IDS:
                destination_channel = self.get_channel(destination_channel_id)
                if not destination_channel:
                    continue

                try:
                    if content:
                        forwarded_message = await destination_channel.send(content=content)
                    forwarded_image = await destination_channel.send(file=discord.File(io.BytesIO(file_content), filename=attachment.filename, spoiler=attachment.is_spoiler()))

                    self.forwarded_messages[message.id] = self.forwarded_messages.get(message.id, []) + [(destination_channel_id, forwarded_message.id if content else None, forwarded_image.id)]
                except discord.HTTPException:
                    continue
        else:
            await asyncio.sleep(3)
            updated_message = await message.channel.fetch_message(message.id)
            if updated_message.attachments:
                await self.process_message(updated_message)

    async def queue_processor(self):
        while True:
            if self.message_queue:
                message = self.message_queue.popleft()
                await self.process_message(message)
                # Update the last processed message ID for the source channel
                self.last_message_ids[message.channel.id] = message.id
            await asyncio.sleep(1)  # Adjust sleep time if necessary

    @tasks.loop(seconds=10)
    async def forward_task(self):
        for source_channel_id in SOURCE_CHANNEL_IDS:
            source_channel = self.get_channel(source_channel_id)
            if not source_channel:
                continue

            async for message in source_channel.history(limit=5):
                if (self.last_message_ids[source_channel_id] is None or
                        message.id > self.last_message_ids[source_channel_id]):
                    if message.id not in self.forwarded_messages:
                        self.message_queue.append(message)

    async def on_message_delete(self, message):
        if message.channel.id in SOURCE_CHANNEL_IDS and message.id in self.forwarded_messages:
            for destination_channel_id, forwarded_message_id, forwarded_image_id in self.forwarded_messages[message.id]:
                destination_channel = self.get_channel(destination_channel_id)
                if destination_channel:
                    try:
                        if forwarded_message_id:
                            forwarded_message = await destination_channel.fetch_message(forwarded_message_id)
                            await forwarded_message.delete()
                        if forwarded_image_id:
                            forwarded_image = await destination_channel.fetch_message(forwarded_image_id)
                            await forwarded_image.delete()
                    except discord.HTTPException:
                        continue
            del self.forwarded_messages[message.id]

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        self.forward_task.start()
        self.loop.create_task(self.queue_processor())

if __name__ == '__main__':
    keep_alive()  # Call the keep_alive function to start the Flask server
    bot = ForwardingBot()
    bot.run(BOT_TOKEN)
