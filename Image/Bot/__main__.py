from settings import *
import pymongo
from loguru import logger
import nextcord
from nextcord.ext import commands
import asyncio

cogs = []


bot = commands.Bot(command_prefix=bot_prefix, intents=nextcord.Intents.all())


def initialize_cogs():
    if music:
        cogs.append("cogs.music.music")
        cogs.append('cogs.presence.presence')
    if moderation:
        cogs.append("cogs.moderation")
    if general:
        cogs.append("cogs.general")
    if giveaway:
        cogs.append('cogs.giveaway')
    if support:
        cogs.append('cogs.support')

def load_cogs():
    for cog in cogs:
        try:
            bot.load_extension(cog)
            logger.info(f"Loaded {cog}")
        except Exception as e:
            logger.error(f"Failed to load {cog}: {e}")


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user.name} - {bot.user.id}")
    logger.info("Bot is ready")

@bot.slash_command(name='generate-invite', description='Generate an invite link for the bot')
async def generate_invite(interaction: nextcord.Interaction):
    invite_link = nextcord.utils.oauth_url(bot.user.id, permissions=nextcord.Permissions.all())
    # create dm channel
    dm_channel = await interaction.user.create_dm()
    # send the invite link to the dm channel
    await dm_channel.send(f"Invite link: {invite_link}")


initialize_cogs()
load_cogs()
bot.run(bot_token,reconnect=True)