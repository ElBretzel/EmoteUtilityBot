import logging
from sqlite3 import OperationalError, IntegrityError

from discord.ext import commands

from database import DBManager


class EventGuildMemberJoin(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_member_join(self, member):
    
        if member.bot:
            return
        
        logging.info(f"A member joined the guild {member.guild.name}:{member.id} : {member.display_name}:{member.id} .")
        logging.info(f"Populating the database with the information of the member {member.display_name}:{member.id} ...")
        try:
            DBManager().add_new_member(member.guild.id, member.id)
        except (OperationalError, IntegrityError):
            logging.exception(f"Task failed, the database information of the member {member.display_name}:{member.id} has not been created.")
        else:
            logging.info(f"The database information of the member {member.display_name}:{member.id} has been created.")

def setup(client):
    client.add_cog(EventGuildMemberJoin(client))
