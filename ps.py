import discord
from discord.ext import tasks
import asyncio
import os
import io
import time
from collections import deque
from keep_alive import keep_alive  # Import the keep_alive function

# Load environment variable securely (assuming .env file exists)
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Channel IDs (replace with your actual channel IDs)
SOURCE_CHANNEL_IDS = [
    
    1248563358995709962
    # Add more source channel IDs here as needed
]
DESTINATION_CHANNEL_IDS = [
    1248563406101942282,
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
        self.sent_messages_log = {}  # Dictionary to keep track of sent messages with timestamps
        self.startup_time = None  # Variable to store the bot's startup time

    async def process_message(self, message):
        if message.attachments:
            content = message.content.strip() if message.content else ""
            attachment = message.attachments[0]
            file_content = await attachment.read()
            current_time = time.time()

            # Check if the message is a duplicate within the last 24 hours
            if content in self.sent_messages_log:
                for log_entry in self.sent_messages_log[content]:
                    if current_time - log_entry["timestamp"] < 86400:  # 86400 seconds = 24 hours
                        # If a similar message has been sent within the last 24 hours, ignore it
                        return

            for destination_channel_id in DESTINATION_CHANNEL_IDS:
                destination_channel = self.get_channel(destination_channel_id)
                if not destination_channel:
                    continue

                try:
                    if content:
                        forwarded_message = await destination_channel.send(content=content)
                    forwarded_image = await destination_channel.send(file=discord.File(io.BytesIO(file_content), filename=attachment.filename, spoiler=attachment.is_spoiler()))

                    self.forwarded_messages[message.id] = self.forwarded_messages.get(message.id, []) + [(destination_channel_id, forwarded_message.id if content else None, forwarded_image.id)]
                    
                    # Log the sent message
                    if content not in self.sent_messages_log:
                        self.sent_messages_log[content] = []
                    self.sent_messages_log[content].append({"timestamp": current_time, "attachment_hash": attachment.filename})
                    
                    # Clean up old log entries
                    self.sent_messages_log[content] = [entry for entry in self.sent_messages_log[content] if current_time - entry["timestamp"] < 86400]
                    
                except discord.HTTPException as e:
                    print(f"Failed to forward message {message.id} to {destination_channel_id}: {e}")

    async def on_message(self, message):
        # Process the message
        await self.process_message(message)

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        self.startup_time = time.time()  # Store the bot's startup time

if __name__ == '__main__':
    keep_alive()  # Call the keep_alive function to start the Flask server
    bot = ForwardingBot()
    bot.run(BOT_TOKEN)
