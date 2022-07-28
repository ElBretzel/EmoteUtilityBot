import os
import glob
import sys
import logging
from datetime import datetime
from sqlite3 import OperationalError, IntegrityError

from discord import Intents
from discord.ext import commands

from constants import *
from database import DBManager

# Open discord bot token
with open(os.path.join(KEY_DIRECTORY, "discord-key.txt"), "r") as f:
    TOKEN = f.read()

# Set working directory to current file directory
sys.path.insert(1, DIRECTORY)
os.chdir(DIRECTORY)

# Necessary (to detect some events)
default_intents = Intents.default()
default_intents.members = True
default_intents.typing = False
default_intents.presences = False

# Log to a file

root_logger= logging.getLogger()
root_logger.setLevel(logging.INFO)
handler = logging.FileHandler(os.path.join(LOGS_DIRECTORY, f"{datetime.now().strftime('%y%m%d%H%M%S')}.log"), 'w', 'utf-8')
handler.setFormatter(logging.Formatter("%(levelname)s - %(asctime)s : %(message)s", datefmt=r'%Y/%m/%d %H:%M:%S'))
root_logger.addHandler(handler)

class Bot(commands.Bot):
    def __init__(self, token, prefix):
        self.token = token
        self.prefix = prefix
        super().__init__(command_prefix = self.prefix, intents = default_intents, reconnect = True)
        
    def load_commands(self):
        # * Import and load all commands (cogs)
        cogs_file = glob.iglob(f"{COGS_DIRECTORY}**.py")
        for files in cogs_file:
            files = files.split(f"{OS_SLASH}")[-1][:-3]
            logging.info(f"Starting cog {files} .")
            try:
                self.load_extension(f'cogs.{files}')
            except commands.NoEntryPointError:
                logging.error("The cog does not have a setup function.")
            except commands.ExtensionFailed:
                logging.exception("The cog or its setup function had an execution error.")

    def load_events(self):
        # * Import and load all events (cogs)
        event_file = glob.iglob(f"{EVENTS_DIRECTORY}**.py")
        for files in event_file:
            files = files.split(f"{OS_SLASH}")[-1][:-3]
            logging.info(f"Starting event {files} .")
            try:
                self.load_extension(f'events.{files}')
            except commands.NoEntryPointError:
                logging.error("The event does not have a setup function.")
            except commands.ExtensionFailed:
                logging.exception("The event or its setup function had an execution error.")
    
    def start_bot(self):

        logging.info("Deleting help command...")
        self.remove_command('help')
        logging.info("Done!")
        logging.info("Checking database...")
        DBManager()
        logging.info("Done!")
        logging.info("Loading cogs...")
        self.load_commands()
        logging.info("Done!")
        logging.info("Loading events...")
        self.load_events()
        logging.info("Done!")
        logging.info("Bot launching...")
        self.run(self.token)


    def _populate_guild(self, guild):
        try:
            DBManager().add_new_guild(guild.id)
        except (OperationalError, IntegrityError):
            logging.exception(f"Task failed, the database information of the guild {guild.name}:{guild.id} has not been checked.")
        else:
            logging.debug(f"The database information of the guild {guild.name}:{guild.id} has been checked.")

    def _populate_member(self, guild, member):
        try:
            DBManager().add_new_member(guild.id, member.id)
        except (OperationalError, IntegrityError):
            logging.exception(f"Task failed, the database information of the member {member.display_name}:{member.id} has not been checked.")
        else:
            logging.debug(f"The database information of the member {member.display_name}:{member.id} has been checked.")

    def _populate_emoji(self, guild, emoji):
        try:
            DBManager().add_new_emoji(guild.id, emoji.id)
        except (OperationalError, IntegrityError):
            logging.exception(f"Task failed, the database information of the emoji {emoji.name}:{emoji.id} has not been checked.")
        else:
            logging.debug(f"The database information of the emoji {emoji.name}:{emoji.id} has been checked.")
        
    async def on_ready(self):
        logging.info("Checking the integrity of the database...")

        for guild in self.guilds:
            logging.info(f"Checking guild {guild.name}:{guild.id} ...")
            self._populate_guild(guild)

            guild_obj = await self.fetch_guild(guild.id)
            for emoji in guild_obj.emojis:
                logging.debug(f"Checking emoji {emoji.name}:{emoji.id} ...")
                self._populate_emoji(guild, emoji)

            for member in guild.members:

                if member.bot:
                    continue

                logging.debug(f"Checking member {member.display_name}:{member.id} ...")
                self._populate_member(guild, member)

        logging.info("Bot is ready!")

        print("{:-^30}".format(""))  
        print(f"Bot lancé avec succès!\nLien d'invitation: https://discord.com/api/oauth2/authorize?client_id={self.user.id}&permissions=8&scope=bot")
        print(f"Status: {round(self.latency, 3)*(10**3)} ms")
        print("{:-^30}".format(""))


if __name__ == "__main__":

    client = Bot(TOKEN, PREFIX)
    client.start_bot()


# TODO uvloop