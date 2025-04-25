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
        self.played_songs = set()
    

    def get_youtube_music_recommendation(self,video_id: str):
        # Initialize YTMusic
        ytmusic = YTMusic()

        radio = ytmusic.get_watch_playlist(videoId=video_id)
        new_tracks = []

        for track in radio['tracks']:
            track_id = track['videoId']
            if track_id not in self.played_songs:
                new_tracks.append(track)
                self.played_songs.add(track_id)
        return new_tracks

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

                tracks = self.get_youtube_music_recommendation(track.identifier)
                tracks.pop(0)
                if not tracks:
                    return
                res = await player.fetch_tracks(f'https://youtube.com/watch?v={tracks[0]["videoId"]}')
                await player.play(res[0])
                
            elif event.reason == EndReason.STOPPED:
                logger.warning(f"Autoplay enabled for guild {guild_id}")
                track = event.track
                player = event.player
                tracks = self.get_youtube_music_recommendation(track.identifier)
                tracks.pop(0)
                if not tracks:
                    return
                res = await player.fetch_tracks(f'https://youtube.com/watch?v={tracks[0]["videoId"]}')
                await player.play(res[0])
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
            if self.loop_modes.get(guild_id) == "random":
                if queue := self.guild_queues.get(guild_id):
                    if len(queue) >= 1:
                        random_track = random.choice(queue)
                        queue.remove(random_track)
                        await player.play(random_track)
                        return

            if queue := self.guild_queues.get(guild_id):
                next_track = queue.pop(0)
                await player.play(next_track)
                return

            await player.disconnect()
            self.guild_queues[guild_id].clear()
            self.loop_modes[guild_id] = False
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
                title="🎵 Şuan Çalıyor 🎵",
                color=nextcord.Color.green()
            )
            embed.add_field(name="Şarkı", value=f"**{track.title}**", inline=False)
            embed.add_field(name="Sanatçı", value=f"**{track.author}**", inline=False)
            embed.add_field(name="Kaynak", value=f"{track.source}", inline=False)
            embed.set_thumbnail(url=track.artwork_url)
            channel = self.bot.get_channel(self.command_channels.get(player.guild.id))
            return await channel.send(embed=embed)
        else:
            track = event.track
            embed = nextcord.Embed(
                title="🎵 Şuan Çalıyor 🎵",
                color=nextcord.Color.green()
            )
            embed.add_field(name="Şarkı", value=f"**{track.title}**", inline=False)
            embed.add_field(name="Sanatçı", value=f"**{track.author}**", inline=False)
            embed.add_field(name="Kaynak", value=f"{track.source}", inline=False)
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
