import logging
from sqlite3 import OperationalError, IntegrityError

from discord.ext import commands

from database import DBManager


class EventGuildEmoteUpdate(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def add_emoji(self, guild, emoji):

        emoji = next(iter(emoji))
        logging.info(f"The guild {guild.name}:{guild.id} has added a new emoji: {emoji.name}:{emoji.id} .")
        logging.info(f"Populating the database with the information of the emoji {emoji.name}:{emoji.id} ...")

        try:
            DBManager().add_new_emoji(guild.id, emoji.id)
        except (OperationalError, IntegrityError):
            logging.exception(f"Task failed, the database information of the emoji {emoji.name}:{emoji.id} has not been created.")
        else:
            logging.info(f"The database information of the emoji {emoji.name}:{emoji.id} has been created.")

    async def remove_emoji(self, guild, emoji):

        emoji = next(iter(emoji))
        logging.info(f"The guild {guild.name}:{guild.id} has removed an emoji: {emoji.name}:{emoji.id} .")
        logging.info(f"Cleaning up the database informations of the emoji {emoji.name}:{emoji.id} ...")
        
        try:
            DBManager().remove_existing_emoji(guild.id, emoji.id)
        except (OperationalError, IntegrityError):
            logging.exception(f"Task failed, the database information of the emoji {emoji.name}:{emoji.id} has not been deleted.")
        else:
            logging.info(f"The database information of the emoji {emoji.name}:{emoji.id} has been deleted.")
        
        for member in guild.members:
            try:
                DBManager().remove_emoji_member(member.id, guild.id, emoji.id)
            except OperationalError:
                logging.exception(f"Task failed, the database information of the emoji {emoji.name}:{emoji.id} has not been deleted from the member {member.display_name}:{member.id}.")
            else:
                logging.debug(f"The database information of the emoji {emoji.name}:{emoji.id} has been deleted from the member {member.display_name}:{member.id}.")

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        before_emotes = set(before)
        after_emotes = set(after)

        if len(before) > len(after):
            await self.remove_emoji(guild, before_emotes - after_emotes)
        else:
            await self.add_emoji(guild, after_emotes - before_emotes)


def setup(client):
    client.add_cog(EventGuildEmoteUpdate(client))
