import nextcord
from nextcord.ext import commands
from loguru import logger
from settings import *

import mafic
from collections import defaultdict

from .music_commands import MusicCommands
from .music_events import MusicEvents

class Music(MusicCommands, MusicEvents, commands.Cog):
    def __init__(self, bot: commands.Bot):
        MusicCommands.__init__(self, bot)
        MusicEvents.__init__(self, bot)
        # Shared state initialization
        self.guild_queues = defaultdict(list)
        self.loop_modes = defaultdict(lambda: False)
        self.command_channels = {}
        self.last_tracks = {}
        self.inactive_timers = {}
        self.inactive_threshold = 60

def setup(bot: commands.Bot):
    bot.add_cog(Music(bot))
    logger.info("Music cog loaded")