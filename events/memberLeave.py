import logging
from sqlite3 import OperationalError, IntegrityError

from discord.ext import commands

from database import DBManager


class EventGuildMemberLeave(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        logging.info(f"A member leaved the guild {member.guild.name}:{member.id} : {member.display_name}:{member.id} .")
        logging.info(f"Cleaning up the database informations of the member {member.display_name}:{member.id} ...")
        try:
            DBManager().remove_existing_member(member.guild.id, member.id)
        except (OperationalError, IntegrityError):
            logging.exception(f"Task failed, the database information of the member {member.display_name}:{member.id} has not been deleted.")
        else:
            logging.info(f"The database information of the member {member.display_name}:{member.id} has been deleted.")

def setup(client):
    client.add_cog(EventGuildMemberLeave(client))
