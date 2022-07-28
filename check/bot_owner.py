import logging

from discord.ext import commands

from constants import DEV

def check_if_bot_owner():
    def predicate(ctx):
        if DEV == ctx.author.id:
            return True

        logging.warning(f"The user {ctx.author.name}:{ctx.author.id} tried to execute a dev only command.")
        ctx.send("Cette commande ne peut être utilisé que par le propriétaire du bot.")
    return commands.check(predicate)
