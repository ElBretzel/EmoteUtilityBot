import logging
from sqlite3 import OperationalError, IntegrityError

from discord.ext import commands

from database import DBManager


class EventGuildLeave(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):

        logging.info(f"The bot was removed from the guild {guild.name}:{guild.id} .")
        logging.info(f"Cleaning up the database informations of the guild {guild.name}:{guild.id} ...")
        try:
            DBManager().remove_existing_guild(guild.id)
        except (OperationalError, IntegrityError):
            logging.exception(f"Task failed, the database information of the guild {guild.name}:{guild.id} has not been deleted.")
        else:
            logging.info(f"The database information of the guild {guild.name}:{guild.id} has been deleted.")

def setup(client):
    client.add_cog(EventGuildLeave(client))
