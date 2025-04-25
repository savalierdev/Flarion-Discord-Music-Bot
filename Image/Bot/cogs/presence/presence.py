import nextcord
from nextcord.ext import commands
from loguru import logger
from cogs.presence.change_presence import ChangePresence



class PresenceEvents(ChangePresence,commands.Cog):
    def __init__(self, bot: commands.Bot):
        ChangePresence.__init__(self, bot)
        self.bot = bot
        logger.info(f"Presence events cog is ready")


def setup(bot: commands.Bot):
    bot.add_cog(PresenceEvents(bot))
    logger.info("Presence events cog loaded")
