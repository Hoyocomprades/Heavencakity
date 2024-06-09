import discord
import asyncio
import os
import io
import time
from keep_alive import keep_alive  # Import the keep_alive function

# Load environment variable securely (assuming .env file exists)
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Channel IDs (replace with your actual channel IDs)
SOURCE_CHANNEL_IDS = [
    1248563358995709962,
    863803391239127090
    # Add more source channel IDs here as needed
]
DESTINATION_CHANNEL_IDS = [
    1248563406101942282,
    1248623054226067577
]

class ForwardingBot(discord.Client):

    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.sent_messages_log = {}  # Dictionary to keep track of sent messages with timestamps and IDs
        self.startup_time = None  # Variable to store the bot's startup time

    async def process_message(self, message):
        if message.channel.id not in SOURCE_CHANNEL_IDS:
            return  # Ignore messages from channels that are not in the source channels

        content = message.content.strip() if message.content else ""
        attachment_content = None

        if message.attachments:
            attachment = message.attachments[0]
            attachment_content = await attachment.read()

        current_time = int(time.time())
        message_key = (message.channel.id, content, attachment.filename if attachment else None)

        # Check if the message is a duplicate within the last 24 hours
        if message_key in self.sent_messages_log:
            last_timestamp = self.sent_messages_log[message_key]['timestamp']
            if current_time - last_timestamp < 86400:  # 86400 seconds = 24 hours
                # If a similar message has been sent within the last 24 hours, ignore it
                return

        forwarded_messages = []
        for destination_channel_id in DESTINATION_CHANNEL_IDS:
            destination_channel = self.get_channel(destination_channel_id)
            if not destination_channel:
                continue

            try:
                if content:
                    forwarded_message = await destination_channel.send(content=content)
                    forwarded_messages.append(forwarded_message.id)
                if attachment_content:
                    forwarded_attachment = await destination_channel.send(file=discord.File(io.BytesIO(attachment_content), filename=attachment.filename, spoiler=attachment.is_spoiler()))
                    forwarded_messages.append(forwarded_attachment.id)

                # Log the sent message timestamp and forwarded message IDs
                self.sent_messages_log[message_key] = {'timestamp': current_time, 'forwarded_messages': forwarded_messages}
                    
            except discord.HTTPException as e:
                print(f"Failed to forward message to {destination_channel_id}: {e}")

    async def process_deleted_message(self, message):
        # Delete corresponding messages from target channels when a message is deleted from source channel
        content = message.content.strip() if message.content else ""
        attachment_filename = message.attachments[0].filename if message.attachments else None
        message_key = (message.channel.id, content, attachment_filename)

        if message_key in self.sent_messages_log:
            forwarded_messages = self.sent_messages_log[message_key]['forwarded_messages']
            for destination_channel_id in DESTINATION_CHANNEL_IDS:
                destination_channel = self.get_channel(destination_channel_id)
                if not destination_channel:
                    continue

                try:
                    for forwarded_message_id in forwarded_messages:
                        forwarded_message = await destination_channel.fetch_message(forwarded_message_id)
                        await forwarded_message.delete()

                except discord.HTTPException as e:
                    print(f"Failed to delete message from {destination_channel_id}: {e}")

            # Remove the entry from the log
            del self.sent_messages_log[message_key]

    async def on_message(self, message):
        # Process the message
        await self.process_message(message)

    async def on_message_delete(self, message):
        # Process the deleted message
        await self.process_deleted_message(message)

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        self.startup_time = int(time.time())  # Store the bot's startup time

if __name__ == '__main__':
    keep_alive()  # Call the keep_alive function to start the Flask server
    bot = ForwardingBot()
    bot.run(BOT_TOKEN)
