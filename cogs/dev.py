import logging

from discord.ext import commands

from check.bot_owner import check_if_bot_owner
from constants import PREFIX

class Development(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    @commands.check_any(check_if_bot_owner())
    async def load(self, ctx, module : str):
        logging.info(f"The user {ctx.author.name}:{ctx.author.id} has entered the command {PREFIX}load {module}.")
        try:
            self.client.load_extension(f"cogs.{module}")
        except Exception as e:
            logging.exception(f"Failed to load the module {module} .")
            await ctx.send(f"Une erreur est survenue lors du chargement du module **{module}**: {e}")
        else:
            await ctx.send(f"**{module}** chargé.", delete_after=5)

    @commands.command()
    @commands.check_any(check_if_bot_owner())
    async def unload(self, ctx, module : str):
        logging.info(f"The user {ctx.author.name}:{ctx.author.id} has entered the command {PREFIX}unload {module} .")
        try:
            self.client.unload_extension(f"cogs.{module}")
        except Exception as e:
            logging.exception(f"Failed to unload the module {module} .")
            await ctx.send(f"Une erreur est survenue lors du déchargement du module {module}: {e}")
        else:
            await ctx.send(f"**{module}** déchargé.", delete_after=5)

    @commands.command()
    @commands.check_any(check_if_bot_owner())
    async def reload(self, ctx, module : str):
        logging.info(f"The user {ctx.author.name}:{ctx.author.id} has entered the command {PREFIX}reload {module} .")
        try:
            self.client.unload_extension(f"cogs.{module}")
            self.client.load_extension(f"cogs.{module}")
        except Exception as e:
            logging.exception(f"Failed to reload the module {module} .")
            await ctx.send(f"Une erreur est survenue lors du rechargement du module {module}: {e}")
        else:
            await ctx.send(f"**{module}** rechargé.", delete_after=5)

def setup(client):
    client.add_cog(Development(client))
