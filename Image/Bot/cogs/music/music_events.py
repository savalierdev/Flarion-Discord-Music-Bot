import nextcord
from nextcord.ext import commands
from loguru import logger
from settings import *

import mafic
from mafic import TrackEndEvent, TrackStartEvent, EndReason
import asyncio
import random
import aiohttp
from ytmusicapi import YTMusic


class MusicEvents:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.nodes = mafic.NodePool(self.bot)
        self.ready_ran = False
        self.inactive_timers = {}
        self.inactive_threshold = 60
        self.guild_queues = {}
        self.loop_modes = {}
        self.command_channels = {}
        self.autoplay_enabled = {}
    

    def get_youtube_music_recommendation(self, query:str):
        # Initialize YTMusic
        self.ytmusic = YTMusic()

        # Search for the query
        search_results = self.ytmusic.get_watch_playlist(videoId=query)

        related_tracks = []
        for track in search_results['tracks']:
            related_tracks.append({
                'title': track['title'],
                'url': track['videoId'],
                'artist': track['artists'][0]['name']
            })
        return related_tracks

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        logger.info(f"Music events cog is ready")
        await self.connect_node()

    @commands.Cog.listener()
    async def on_node_ready(self, node: mafic.Node):
        logger.info(f"Lavalink node {node.label} is ready.")

    async def connect_node(self):
        if self.ready_ran:
            return

        try:
            await self.nodes.create_node(
                host=host,
                port=port,
                label="MAIN",
                password=password,
                secure=secure
            )
            logger.info("Connected to Lavalink node")
        except RuntimeError:
            logger.error("Failed to connect to Lavalink node")

        self.ready_ran = True

    @commands.Cog.listener()
    async def on_track_end(self, event: TrackEndEvent):
        assert isinstance(event.player, mafic.Player)
        assert isinstance(event.track, mafic.Track)
        
        player = event.player
        track = event.track
        guild_id = player.guild.id
        
        # If autoplay is enabled, handle it first
        if self.autoplay_enabled.get(guild_id, False):
            if event.reason == EndReason.FINISHED:
                logger.warning(f"Autoplay enabled for guild {guild_id}")
                track = event.track
                player = event.player
                if track.source == "youtube":
                    # Get recommendations from YouTube Music
                    recommendations = self.get_youtube_music_recommendation(track.identifier)
                    recommendations.pop(0)
                    logger.info(f"Recommendations for {track.title}: {recommendations}")
                    if recommendations:
                        # Play the first recommendation
                        recommended_track = random.choice(recommendations)
                        track_url = f"https://www.youtube.com/watch?v={recommended_track['url']}"
                        results = await player.fetch_tracks(track_url)
                        await player.play(results[0])
                        return
                elif track.source == "spotify":
                    pass
            elif event.reason == EndReason.STOPPED:
                logger.warning(f"Autoplay enabled for guild {guild_id}")
                track = event.track
                player = event.player
                if track.source == "youtube":
                    # Get recommendations from YouTube Music
                    recommendations = self.get_youtube_music_recommendation(track.identifier)
                    recommendations.pop(0)  # Remove the current track from recommendations
                    logger.info(f"Recommendations for {track.title}: {recommendations}")
                    if recommendations:
                        # Play the first recommendation
                        recommended_track = random.choice(recommendations)
                        track_url = f"https://www.youtube.com/watch?v={recommended_track['url']}"
                        results = await player.fetch_tracks(track_url)
                        await player.play(results[0])
                        return
                    else:
                        logger.error(f"No recommendations found for {track.title}")
                elif track.source == "spotify":
                    pass
            return

        # Handle finished tracks
        if event.reason == EndReason.FINISHED:
            autoplay_mode = self.autoplay_enabled.get(guild_id)
            loop_mode = self.loop_modes.get(guild_id)
            
            if loop_mode == "track":
                await player.play(track)
                return
                
            elif loop_mode == "queue":
                if queue := self.guild_queues.get(guild_id):
                    queue.append(track)
                    logger.debug(f"Queue for guild {guild_id}: {queue}")
                    next_track = queue.pop(0)
                    await player.play(next_track)
                    return
                    
            elif loop_mode == "random":
                if queue := self.guild_queues.get(guild_id):
                    if len(queue) >= 1:
                        random_track = random.choice(queue)
                        queue.remove(random_track)
                        await player.play(random_track)
                        return
            
            # If no loop mode or queue is empty
            if queue := self.guild_queues.get(guild_id):
                next_track = queue.pop(0)
                await player.play(next_track)
                return
            
            # No more tracks to play
            await player.disconnect()
            self.guild_queues[guild_id].clear()
            self.loop_modes[guild_id] = False
            return

        # Handle stopped tracks
        elif event.reason == EndReason.STOPPED:
            if queue := self.guild_queues.get(guild_id):
                next_track = queue.pop(0)
                await player.play(next_track)
                return

    @commands.Cog.listener()
    async def on_track_start(self, event: TrackStartEvent):
        assert isinstance(event.player, mafic.Player)
        assert isinstance(event.track, mafic.Track)

        player = event.player
        guild_loop_mode = self.loop_modes.get(player.guild.id)

        if guild_loop_mode == "track":
            return
        elif guild_loop_mode == "queue":
            track = event.track
            embed = nextcord.Embed(
                title="Şuan Çalıyor",
                description=f"**{track.title}** by **{track.author}**",
                color=nextcord.Color.green()
            )
            embed.set_thumbnail(url=track.artwork_url)
            channel = self.bot.get_channel(self.command_channels.get(player.guild.id))
            return await channel.send(embed=embed)
        else:
            track = event.track
            embed = nextcord.Embed(
                title="Şuan Çalıyor",
                description=f"**{track.title}** by **{track.author}**",
                color=nextcord.Color.green()
            )
            embed.set_thumbnail(url=track.artwork_url)
            channel = self.bot.get_channel(self.command_channels.get(player.guild.id))
            return await channel.send(embed=embed)
          
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id == self.bot.user.id:
            if not before.channel and after.channel:
                guild_id = after.channel.guild.id
                
                if guild_id in self.inactive_timers:
                    self.inactive_timers[guild_id].cancel()
                
                async def check_inactivity():
                    await asyncio.sleep(300)
                    player: mafic.Player = self.bot.get_guild(guild_id).voice_client
                    if player and not player.current:
                        channel = self.bot.get_channel(self.command_channels.get(guild_id))
                        if channel:
                            embed = nextcord.Embed(
                                title="Disconnected due to inactivity",
                                description="Left the voice channel after 5 minutes of inactivity.",
                                color=nextcord.Color.red()
                            )
                            await channel.send(embed=embed)
                        await player.disconnect()
                        self.guild_queues[guild_id].clear()
                        self.loop_modes[guild_id] = False
                    
                    if guild_id in self.inactive_timers:
                        del self.inactive_timers[guild_id]
                
                self.inactive_timers[guild_id] = self.bot.loop.create_task(check_inactivity())
            
            elif before.channel and not after.channel:
                guild_id = before.channel.guild.id
                if guild_id in self.inactive_timers:
                    self.inactive_timers[guild_id].cancel()
                    del self.inactive_timers[guild_id]

def setup(bot: commands.Bot):
    bot.add_cog(MusicEvents(bot))
    logger.info("Music events cog loaded")
