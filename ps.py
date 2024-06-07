import discord
from discord.ext import tasks
import asyncio
import os
import io
import logging
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

# Set up logging
logging.basicConfig(level=logging.INFO)

class ForwardingBot(discord.Client):

    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True  # Enable message intents
        super().__init__(intents=intents)
        self.last_message_ids = {channel_id: None for channel_id in SOURCE_CHANNEL_IDS}
        self.forwarded_messages = set()  # Set to keep track of forwarded message IDs

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
                    if message.id not in self.forwarded_messages:  # Check if message has already been forwarded
                        if content:
                            forwarded_message = await destination_channel.send(content=content)
                            logging.info(f"Forwarded message content to {destination_channel}")
                        if file_content:
                            forwarded_image = await destination_channel.send(file=discord.File(io.BytesIO(file_content), filename=attachment.filename, spoiler=attachment.is_spoiler()))
                            logging.info(f"Forwarded image to {destination_channel}")

                        self.forwarded_messages.add(message.id)  # Add message ID to set of forwarded messages
                except discord.HTTPException as e:
                    logging.error(f"Error forwarding message to {destination_channel}: {e}")
        else:
            await asyncio.sleep(3)
            updated_message = await message.channel.fetch_message(message.id)
            if updated_message.attachments:
                await self.process_message(updated_message)

    @tasks.loop(seconds=10)
    async def forward_task(self):
        for source_channel_id in SOURCE_CHANNEL_IDS:
            source_channel = self.get_channel(source_channel_id)
            if not source_channel:
                continue

            async for message in source_channel.history(limit=1):
                if self.last_message_ids[source_channel_id] is None or message.id != self.last_message_ids[source_channel_id]:
                    self.last_message_ids[source_channel_id] = message.id
                    await self.process_message(message)

    async def on_message_delete(self, message):
        if message.id in self.forwarded_messages:
            self.forwarded_messages.remove(message.id)

    async def on_ready(self):
        self.forward_task.start()
        logging.info('Bot is ready.')

if __name__ == '__main__':
    keep_alive()  # Call the keep_alive function to start the Flask server
    bot = ForwardingBot()
    bot.run(BOT_TOKEN)
