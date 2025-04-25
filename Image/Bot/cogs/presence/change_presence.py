import nextcord
from nextcord.ext import commands
from loguru import logger
import asyncio
import random


class ChangePresence:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Change presence cog is ready")
        # Botun Durumunu Belirli Aralıklarla Değiştir
        
        statuses = [
            nextcord.Activity(type=nextcord.ActivityType.listening, name="/play | made by Flarion Development Team"),
            nextcord.Activity(type=nextcord.ActivityType.watching, name="müzik dinleyenleri"),
            nextcord.Activity(type=nextcord.ActivityType.playing, name="en iyi müzikleri"),
            nextcord.Activity(type=nextcord.ActivityType.listening, name="komutlarınızı")
        ]
        
        import random
        await self.bot.change_presence(activity=random.choice(statuses))
        
        # Her 5 dakikada bir durumu değiştir
        import asyncio
        self.bot.loop.create_task(self.change_presence_periodically(statuses))
        
        
    async def change_presence_periodically(self, statuses):
        while True:
            await asyncio.sleep(20)
            await self.bot.change_presence(activity=random.choice(statuses))
        
    def setup(bot: commands.Bot):
        bot.add_cog(ChangePresence(bot))
        logger.info("Change presence cog loaded")
