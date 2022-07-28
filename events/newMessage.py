import logging
import re
from sqlite3 import OperationalError

import discord
from discord.ext import commands

from database import DBManager


def close_connexion(connexion):
    connexion.commit()
    connexion.close()


class EventMemberMessage(commands.Cog):
    def __init__(self, client):
        self.client = client


    @commands.Cog.listener()
    async def on_message(self, message):

        if message.type != discord.MessageType.default or\
            message.author.bot or\
            message.channel.type in [discord.ChannelType.private, discord.ChannelType.group,
                                     discord.ChannelType.news, discord.ChannelType.store]:

            return

        found_emoji_id = map(lambda x: int(x), re.findall(r"(?:<?:\w+:)([^:][\d]*(?:::[^:][\d]*)*)>", message.content))
        for emoji in map(lambda i: self.client.get_emoji(i), found_emoji_id):

            if not emoji:
                continue
            if emoji.guild_id != message.guild.id:
                continue

            logging.info(f"Found an emoji on the message {message.content}{message.id} sent by {message.author.display_name}:{message.author.id} on {message.guild.name}:{message.guild.id} :  {emoji.name}:{emoji.id} .")
            logging.info(f"Increasing the counter of the emoji {emoji.name}:{emoji.id} for the member {message.author.display_name}:{message.author.id}")
            try:
                DBManager().add_emoji_member(message.author.id, message.guild.id, emoji.id)
            except OperationalError:
                logging.exception(f"Task failed, the emoji counter {emoji.name}:{emoji.id} of the member {message.author.display_name}:{message.author.id} has not been increased.")
            else:
                logging.info(f"The emoji counter {emoji.name}:{emoji.id} of the member {message.author.display_name}:{message.author.id} has been increased.")

            logging.info(f"Increasing the counter of the emoji {emoji.name}:{emoji.id} for the guild {message.guild.name}:{message.guild.id}")
            try:
                DBManager().add_global_emoji_use(message.guild.id, emoji.id)
            except OperationalError:
                logging.exception(f"Task failed, the emoji counter {emoji.name}:{emoji.id} of the guild {message.guild.name}:{message.guild.id} has not been increased.")
            else:
                logging.info(f"The emoji counter {emoji.name}:{emoji.id} of the guild {message.guild.name}:{message.guild.id} has been increased.")

    
def setup(client):
    client.add_cog(EventMemberMessage(client))
