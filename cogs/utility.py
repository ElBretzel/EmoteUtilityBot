import logging
import re
from sqlite3 import OperationalError, IntegrityError
import discord

from discord.ext import commands
from discord import NotFound, Colour

from events.guildJoin import populate_guild_database
from paginator import PaginatorBuilder, PaginatorController
from database import DBManager
from constants import PREFIX, DEV

class ConvertMember(commands.MemberConverter):
    async def convert(self, ctx, arg):
        user = await super().convert(ctx, arg)
        return user

class Utility(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    async def ping(self, ctx, *args, **kwargs):
        logging.info(f"The user {ctx.author.name}:{ctx.author.id} has entered the command {PREFIX}ping.")
        await ctx.send(f"Pong ({int(self.client.latency*(10**3))}ms)!")

    @commands.command()
    async def pong(self, ctx, *args, **kwargs):
        logging.info(f"The user {ctx.author.name}:{ctx.author.id} has entered the command {PREFIX}pong.")
        await ctx.send(f"Ping ({int(self.client.latency*(10**3))}ms)!")

    async def _check_emoji_exists(self, ctx, emotes):
        logging.info("Checking if all the emoji does exists...")
        try:
            guild_emoji = ([await ctx.guild.fetch_emoji(emoji), use] for emoji, use in emotes)
        except NotFound:
            logging.exception(f"One or multiple emojis do not belong to the guild {ctx.guild.name}:{ctx.guild.id}")
            await ctx.send(f"Une erreur c'est produite, veuillez prévenir l'utilisateur en charge du bot: <@{DEV}>")
        else:
            return guild_emoji

    async def user_emoji(self, ctx, member):

        logging.info(f"Grabbing the emojis used by the member {member.display_name}{member.id} in the guild {ctx.guild.name}:{ctx.guild.id} .")
        user_emotes = DBManager().get_emoji_member(member.id, ctx.guild.id)
        emojis = await self._check_emoji_exists(ctx, user_emotes)
        emojis = [emoji async for emoji in emojis]
        if not emojis:
            await ctx.send(f"{member.display_name} n'a pas encore envoyé(e) d'emoji provenant de ce serveur...", delete_after=60)
            return

        emojis.sort(key=lambda e: e[1], reverse=True)

        content = [f"{emoji}**{emoji.name}  ➙  {count}**" for emoji, count in emojis]
        
        logging.info(f"Creating a paginator for the command {PREFIX}emoji {''.join(str(member.id))} entered by the user {ctx.author.name}:{ctx.author.id} .")
        paginator = PaginatorController(self.client, ctx.author, ctx.channel)
        logging.debug(f"Controller created")
        paginator.builder = PaginatorBuilder()
        logging.debug(f"Builder created")
        paginator.builder.base_embed_create(f"🌟 Liste des emojis utilisés par {member.display_name}",
                                  f"❓ Le nombre après la flèche représente le nombre de fois où l'emoji a été utilisé.",
                                  Colour.gold(),
                                  field=[["📉 Trie:", " Par utilisation décroissante.", True], ["👉 Emote:", "Uniquement un membre.", True], ["\u200b", "\u200b", True]])
        paginator.builder.prefix = "⭒"
        paginator.builder.content = content
        paginator.builder.max_content = 25
        paginator.builder.content_builder(decorator="  ", separator="\n")
        paginator.builder.paginator_store()
        logging.debug(f"Paginator stored and will be posted")
        
        await paginator.paginator_static()
        logging.info(f"Paginator created by the user {ctx.author.name}:{ctx.author.id} has been destroyed.")

    async def guild_emoji(self, ctx):

        logging.info(f"Grabbing the emojis used by the guild {ctx.guild.name}:{ctx.guild.id} .")
        guild_emotes = DBManager().get_guild_emoji(ctx.guild.id)

        emojis = await self._check_emoji_exists(ctx, guild_emotes)
        emojis = [emoji async for emoji in emojis]

        if not emojis:
            await ctx.send("Oups! Le serveur ne possède aucun emoji personnalisé...", delete_after=60)
            return

        emojis.sort(key=lambda e: e[1], reverse=True)

        content = [f"{emoji}**{emoji.name}  ➙  {count}**" for emoji, count in emojis]

        logging.info(f"Creating a paginator for the command {PREFIX}emoji entered by the user {ctx.author.name}:{ctx.author.id} .")
        paginator = PaginatorController(self.client, ctx.author, ctx.channel)
        logging.debug(f"Controller created")
        paginator.builder = PaginatorBuilder()
        logging.debug(f"Builder created")
        paginator.builder.base_embed_create(f"🌟 Liste des emojis utilisés sur le serveur",
                                  f"❓ Le nombre après la flèche représente le nombre de fois où l'emoji a été utilisé.",
                                  Colour.gold(),
                                  field=[["📉 Trie:", " Par utilisation décroissante.", True], ["👉 Emote:", "Tout membre confondu.", True], ["\u200b", "\u200b", True]])
        paginator.builder.prefix = "⭒"
        paginator.builder.content = content
        paginator.builder.max_content = 25
        paginator.builder.content_builder(decorator="  ", separator="\n")
        paginator.builder.paginator_store()
        logging.debug(f"Paginator stored and will be posted")
        
        result = await paginator.paginator_static()
        if isinstance(result, bool):
            await paginator.message.delete()
        logging.info(f"Paginator created by the user {ctx.author.name}:{ctx.author.id} has been destroyed.")

    @commands.command(aliases=['emojis', 'emote', 'emotes'])
    async def emoji(self, ctx, *member: ConvertMember, **kwargs):
        await ctx.send("Veillez patienter...", delete_after=3)
        try:
            await ctx.message.delete()
        except discord.errors.Forbidden:
            pass

        logging.info(f"The user {ctx.author.name}:{ctx.author.id} has entered the command {PREFIX}emoji {''.join(str(member[0].id)) if member else ''} .")
        if member:
            await self.user_emoji(ctx, member[0])
        else:
            await self.guild_emoji(ctx)

    def _scan_emoji(self, message):
        found_emoji_id = map(lambda x: int(x), re.findall(r"(?:<?:\w+:)([^:][\d]*(?:::[^:][\d]*)*)>", message.content))
        emojis = []
        for emoji in map(lambda i: self.client.get_emoji(i), found_emoji_id):

            if not emoji:
                logging.warning(f"{emoji} is not a valid emoji.")
                continue
            if emoji.guild_id != message.guild.id:
                logging.warning(f"The emoji {emoji.name}{emoji.id} do not belongs to the guild {message.guild.name}{message.guild.id} .")
                continue

            emojis.append(emoji.id)
        return emojis

    def _reset_guild_emotes(self, ctx):
        logging.info(f"Deleting the informations of the guild {ctx.guild.name}:{ctx.guild.id} .")
        try:
            DBManager().remove_existing_guild(ctx.guild.id)
        except (OperationalError, IntegrityError):
            logging.exception(f"Task failed, the database information of the guild {ctx.guild.name}:{ctx.guild.id} has not been deleted.")
        else:
            logging.info(f"The database information of the guild {ctx.guild.name}:{ctx.guild.id} has been deleted.")

        logging.info(f"Populating the informations of the guild {ctx.guild.name}:{ctx.guild.id} .")

        populate_guild_database(ctx.guild)

    async def _checking_channels_history(self, ctx, user_emote):
        for channel in ctx.guild.text_channels:
            logging.info(f"Checking the history of the text channel {channel.name}:{channel.id} from the guild {ctx.guild.name}:{ctx.guild.id} .")

            try:
                async for message in channel.history(limit=None):
                    for emoji in self._scan_emoji(message):
                        logging.debug(f"New emoji found: {emoji}")
                        user_emote[message.author.id] =  [[e[0], e[1] + 1] if e[0] == emoji else e for e in user_emote[message.author.id]]
            except discord.errors.Forbidden:
                continue

    async def _increase_member_counter(self, ctx, user_emote, global_emoji):
        for user_id, emojis in user_emote.items():
            user = self.client.get_user(user_id)
            logging.info(f"Increasing the counter of emojis for the user {user.name}:{user_id}")
            for emoji_id, use in emojis:
                logging.debug(f"Adding {emoji_id} to {user_id}")
                emoji = await ctx.guild.fetch_emoji(emoji_id)
                try:
                    DBManager().add_emoji_member(user_id, ctx.guild.id, emoji_id, number=use)
                except OperationalError:
                    logging.exception(f"Task failed, the emoji counter {emoji.name}:{emoji_id} of the user {user.name}:{user_id} has not been increased.")
                else:
                    logging.info(f"The emoji counter {emoji.name}:{emoji_id} of the user {user.name}:{user_id} has been increased.")
                    global_emoji[emoji_id] += use

    async def _increase_global_counter(self, ctx, global_emoji):
        for key, value in global_emoji.items():
            emoji = await ctx.guild.fetch_emoji(key)
            logging.info(f"Increasing the counter of the emoji {emoji.name}:{key} for the guild {ctx.guild.name}:{ctx.guild.id}")
            try:
                DBManager().add_global_emoji_use(ctx.guild.id, key, value)
            except OperationalError:
                logging.exception(f"Task failed, the emoji counter {emoji.name}:{key} of the guild {ctx.guild.name}:{ctx.guild.id} has not been increased.")
            else:
                logging.info(f"The emoji counter {emoji.name}:{key} of the guild {ctx.guild.name}:{ctx.guild.id} has been increased.")


    @commands.command()
    @commands.is_owner()
    async def scanall(self, ctx):
        await ctx.send("Veillez patienter...", delete_after=3)
        try:
            await ctx.message.delete()
        except discord.errors.Forbidden:
            pass

        logging.info(f"The user {ctx.author.name}:{ctx.author.id} has entered the command {PREFIX}scanall .")

        user_emote = {user.id: [[emoji.id, 0] for emoji in ctx.guild.emojis] for user in ctx.guild.members if not user.bot}
        global_emoji = {emoji.id: 0 for emoji in ctx.guild.emojis}

        self._reset_guild_emotes(ctx)
        await self._checking_channels_history(ctx, user_emote)
        await  self._increase_member_counter(ctx, user_emote, global_emoji)
        await self._increase_global_counter(ctx, global_emoji)

        await ctx.send("Base de donnée alimentée!", delete_after=3)

def setup(client):
    client.add_cog(Utility(client))
