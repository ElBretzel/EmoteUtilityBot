import logging
from sqlite3 import OperationalError, IntegrityError

from discord.ext import commands

from database import DBManager



def _populate_guild(guild):
    try:
        DBManager().add_new_guild(guild.id)
    except (OperationalError, IntegrityError):
        logging.exception(f"Task failed, the database information of the guild {guild.name}:{guild.id} has not been created.")
    else:
        logging.info(f"The database information of the guild {guild.name}:{guild.id} has been created.")


def _populate_member(guild, member):
    try:
        DBManager().add_new_member(guild.id, member.id)
    except (OperationalError, IntegrityError):
        logging.exception(f"Task failed, the database information of the member {member.display_name}:{member.id} has not been created.")
    else:
        logging.info(f"The database information of the member {member.display_name}:{member.id} has been created.")


def _populate_emoji(guild, emoji):
    try:
        DBManager().add_new_emoji(guild.id, emoji.id)
    except (OperationalError, IntegrityError):
        logging.exception(f"Task failed, the database information of the emoji {emoji.name}:{emoji.id} has not been created.")
    else:
        logging.info(f"The database information of the emoji {emoji.name}:{emoji.id} has been created.")

def populate_guild_database(guild):
    _populate_guild(guild)
    for member in guild.members:

        if member.bot:
            continue

        logging.debug(f"New member added in the database - {member.display_name}:{member.id}")
        _populate_member(guild, member)

    for emoji in guild.emojis:
        logging.debug(f"New emoji added in  the database- {emoji.name}:{emoji.id}")
        _populate_emoji(guild, emoji)

class EventGuildBotJoin(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_guild_join(self, guild):

        logging.info(f"The bot has been invited in a new guild: {guild.name}:{guild.id} .")
        logging.info(f"Populating the database with the information of the guild {guild.name}:{guild.id} ...")
        populate_guild_database(guild)

def setup(client):
    client.add_cog(EventGuildBotJoin(client))
