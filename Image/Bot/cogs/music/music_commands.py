import nextcord
from nextcord.ext import commands
from loguru import logger
from settings import *

import mafic
from mafic import Player, Track
from collections import defaultdict,deque
import random

class MusicCommands:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild_queues = defaultdict(list)
        self.loop_modes = defaultdict(lambda: False)
        self.autoplay_enabled = defaultdict(lambda: False)
        self.command_channels = {}
        self.last_tracks = {}

    @nextcord.slash_command(name='join', description='Join your voice channel')
    async def join(self, interaction: nextcord.Interaction):
        assert isinstance(interaction.user, nextcord.Member)
        
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
        
        chid = interaction.user.voice.channel
        await chid.connect(cls=mafic.Player)
        await interaction.response.send_message(f"Joined {chid.name}.", ephemeral=True)

    @nextcord.slash_command(name='leave', description='Leave the voice channel')
    async def leave(self, interaction: nextcord.Interaction):
        assert isinstance(interaction.user, nextcord.Member)
        await interaction.response.defer(ephemeral=True,with_message=True)
        
        player: mafic.Player = interaction.guild.voice_client
        if not interaction.user.voice:
            return await interaction.followup.send("You need to be in a voice channel to use this command.", ephemeral=True)
        
        if not interaction.guild.voice_client:
            return await interaction.followup.send("I'm not in a voice channel.", ephemeral=True)

        embed = nextcord.Embed(
            title="Left Voice Channel",
            color=nextcord.Color.red()
        )
        embed.add_field(name="Channel", value='Götünüzü Sikerek Sunucudan Ayrılıyorum')

        await interaction.followup.send(embed=embed, ephemeral=True)
        await player.stop()
        await player.disconnect()
        guild_id = interaction.guild.id
        self.guild_queues[guild_id].clear()
        self.loop_modes[guild_id] = False



    @nextcord.slash_command(name='play', description='Play a song')
    async def play(self, interaction: nextcord.Interaction, *, query: str):
        await interaction.response.defer(ephemeral=True)
        assert isinstance(interaction.user, nextcord.Member)

        guild_id = interaction.guild.id
        self.command_channels[guild_id] = interaction.channel_id

        if not interaction.user.voice:
            return await interaction.followup.send("You need to be in a voice channel to use this command.", ephemeral=True)

        player: mafic.Player = interaction.guild.voice_client
        if not player:
            player = await interaction.user.voice.channel.connect(cls=mafic.Player)

        tracks = await player.fetch_tracks(query)
        if not tracks:
            return await interaction.followup.send("No tracks found.", ephemeral=True)

        #if tracks playlist
        if isinstance(tracks, mafic.Playlist):
            #if player not current playing
            if not player.current:
                await player.play(tracks.tracks[0])
                self.guild_queues[guild_id].extend(tracks.tracks[1:])
                embed = nextcord.Embed(
                    title="Playlist Çalmaya Başladı",
                    description=f"**{tracks.tracks[0].title}** by **{tracks.tracks[0].author}**",
                    color=nextcord.Color.green()
                )
                embed.set_thumbnail(url=tracks.tracks[0].artwork_url)
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                self.guild_queues[guild_id].extend(tracks.tracks)
                embed = nextcord.Embed(
                    title="Sıraya Eklendi",
                    description=f"Added {len(tracks.tracks)} tracks to queue",
                    color=nextcord.Color.blue()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            #if player not current playing
            if not player.current:
                await player.play(tracks[0])
                embed = nextcord.Embed(
                    title="Çalınıyor",
                    description=f"**{tracks[0].title}** by **{tracks[0].author}**",
                    color=nextcord.Color.green()
                )
                embed.set_thumbnail(url=tracks[0].artwork_url)
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                self.guild_queues[guild_id].append(tracks[0])
                embed = nextcord.Embed(
                    title="Sıraya Eklendi",
                    description=f"**{tracks[0].title}** by **{tracks[0].author}** added to queue",
                    color=nextcord.Color.blue()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

    @nextcord.slash_command(name='loop', description='Set loop mode')
    async def loop(self, interaction: nextcord.Interaction, mode: str = nextcord.SlashOption(
        name="mode",
        description="Loop mode to set",
        choices={"Off": "off", "Track": "track", "Queue": "queue","Random":"random"},
        required=True
    )):
        await interaction.response.defer(ephemeral=True)
        assert isinstance(interaction.user, nextcord.Member)

        guild_id = interaction.guild.id
        player: mafic.Player = interaction.guild.voice_client

        if not player:
            return await interaction.followup.send("I'm not in a voice channel.", ephemeral=True)

        if mode == "off":
            self.loop_modes[guild_id] = False
            embed = nextcord.Embed(
                title="Loop Mode",
                description="Loop mode has been turned **off**.",
                color=nextcord.Color.red()
            )
        elif mode == "track":
            self.loop_modes[guild_id] = "track"
            embed = nextcord.Embed(
                title="Loop Mode",
                description="Loop mode has been set to **track**.",
                color=nextcord.Color.green()
            )
        elif mode == "queue":
            self.loop_modes[guild_id] = "queue"
            embed = nextcord.Embed(
                title="Loop Mode",
                description="Loop mode has been set to **queue**.",
                color=nextcord.Color.green()
            )
        elif mode == "random":
            self.loop_modes[guild_id] = "random"
            embed = nextcord.Embed(
                title="Loop Mode",
                description="Loop mode has been set to **random**.",
                color=nextcord.Color.green()
            )

        await interaction.followup.send(embed=embed, ephemeral=True)


    @nextcord.slash_command(name='autoplay', description='Set autoplay mode')
    async def autoplay(self, interaction: nextcord.Interaction, mode: str = nextcord.SlashOption(
        name="mode",
        description="Autoplay mode to set",
        choices={"Off": "off", "On": "on"},
        required=True
    )):
        await interaction.response.defer(ephemeral=True)
        assert isinstance(interaction.user, nextcord.Member)

        guild_id = interaction.guild.id
        player: mafic.Player = interaction.guild.voice_client

        if not player:
            return await interaction.followup.send("I'm not in a voice channel.", ephemeral=True)
        if mode == "off":
            self.autoplay_enabled[guild_id] = False
            embed = nextcord.Embed(
                title="Autoplay Mode",
                description="Autoplay mode has been turned **off**.",
                color=nextcord.Color.red()
            )
        elif mode == "on":
            self.autoplay_enabled[guild_id] = True
            embed = nextcord.Embed(
                title="Autoplay Mode",
                description="Autoplay mode has been turned **on**.",
                color=nextcord.Color.green()
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @nextcord.slash_command(name='skip', description='Skip the current song')
    async def skip(self, interaction: nextcord.Interaction):
        await interaction.response.defer(ephemeral=True)
        assert isinstance(interaction.user, nextcord.Member)

        guild_id = interaction.guild.id
        player: mafic.Player = interaction.guild.voice_client

        if not player:
            return await interaction.followup.send("I'm not in a voice channel.", ephemeral=True)

        if not player.current:
            return await interaction.followup.send("I'm not playing anything.", ephemeral=True)

        await player.stop()
        embed = nextcord.Embed(
            title="Skipped",
            description="The current track has been skipped.",
            color=nextcord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @nextcord.slash_command(name='queue', description='Show the current queue')
    async def queue(self, interaction: nextcord.Interaction):
        await interaction.response.defer(ephemeral=True)
        assert isinstance(interaction.user, nextcord.Member)

        guild_id = interaction.guild.id
        player: mafic.Player = interaction.guild.voice_client

        if not player:
            return await interaction.followup.send("I'm not in a voice channel.", ephemeral=True)

        if not self.guild_queues[guild_id]:
            return await interaction.followup.send("The queue is empty.", ephemeral=True)

        current_track = player.current
        queue = self.guild_queues[guild_id]

        class QueuePaginationView(nextcord.ui.View):
            def __init__(self, queue, current_track=None, timeout=60):
                super().__init__(timeout=timeout)
                self.queue = queue
                self.current_track = current_track
                self.current_page = 0
                self.items_per_page = 10
                self.pages = (len(queue) + self.items_per_page - 1) // self.items_per_page
                
                if self.pages <= 1:
                    self.children[1].disabled = True

            @nextcord.ui.button(label="Previous", style=nextcord.ButtonStyle.blurple)
            async def previous_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
                if self.current_page > 0:
                    self.current_page -= 1
                await interaction.response.edit_message(embed=self.create_embed())

            @nextcord.ui.button(label="Next", style=nextcord.ButtonStyle.blurple)
            async def next_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
                if self.current_page < self.pages - 1:
                    self.current_page += 1
                await interaction.response.edit_message(embed=self.create_embed())

            def create_embed(self):
                start_idx = self.current_page * self.items_per_page
                end_idx = min((self.current_page + 1) * self.items_per_page, len(self.queue))
                
                embed = nextcord.Embed(
                    title="Queue",
                    color=nextcord.Color.blue()
                )
                
                if self.current_track:
                    embed.add_field(
                        name="Now Playing",
                        value=f"**{self.current_track.title}** by **{self.current_track.author}**",
                        inline=False
                    )
                
                if not self.queue:
                    embed.add_field(
                        name="Queue",
                        value="The queue is empty.",
                        inline=False
                    )
                else:
                    queue_text = ""
                    for i in range(start_idx, end_idx):
                        track = self.queue[i]
                        queue_text += f"**{i+1}.** {track.title} - {track.author}\n"
                    
                    embed.add_field(
                        name=f"Queue (Page {self.current_page + 1}/{self.pages})",
                        value=queue_text,
                        inline=False
                    )
                
                return embed

        view = QueuePaginationView(queue, current_track)
        await interaction.followup.send(embed=view.create_embed(), view=view, ephemeral=True)

    @nextcord.slash_command(name='clear', description='Clear the queue')
    async def clear(self, interaction: nextcord.Interaction):
        await interaction.response.defer(ephemeral=True)
        assert isinstance(interaction.user, nextcord.Member)

        guild_id = interaction.guild.id
        player: mafic.Player = interaction.guild.voice_client

        if not player:
            return await interaction.followup.send("I'm not in a voice channel.", ephemeral=True)

        self.guild_queues[guild_id].clear()
        embed = nextcord.Embed(
            title="Queue Cleared",
            description="The queue has been cleared.",
            color=nextcord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @nextcord.slash_command(name='pause', description='Pause the current song')
    async def pause(self, interaction: nextcord.Interaction):
        await interaction.response.defer(ephemeral=True)
        assert isinstance(interaction.user, nextcord.Member)

        player: mafic.Player = interaction.guild.voice_client

        if not player:
            return await interaction.followup.send("I'm not in a voice channel.", ephemeral=True)

        if not player.current:
            return await interaction.followup.send("I'm not playing anything.", ephemeral=True)

        await player.pause()
        embed = nextcord.Embed(
            title="Paused",
            description="The current track has been paused.",
            color=nextcord.Color.orange()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @nextcord.slash_command(name='shuffle', description='Shuffle the queue')
    async def shuffle(self, interaction: nextcord.Interaction):
        await interaction.response.defer(ephemeral=True)
        assert isinstance(interaction.user, nextcord.Member)

        guild_id = interaction.guild.id
        player: mafic.Player = interaction.guild.voice_client

        if not player:
            return await interaction.followup.send("I'm not in a voice channel.", ephemeral=True)

        if len(self.guild_queues[guild_id]) < 2:
            return await interaction.followup.send("There are not enough tracks in the queue to shuffle.", ephemeral=True)

        random.shuffle(self.guild_queues[guild_id])
        embed = nextcord.Embed(
            title="Queue Shuffled",
            description="The queue has been shuffled.",
            color=nextcord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @nextcord.slash_command(name='nowplaying',description='Show Current Track')
    async def nowplaying(self, interaction: nextcord.Interaction):
        assert isinstance(interaction.user, nextcord.Member)
        await interaction.response.defer(ephemeral=True)

        guild_id = interaction.guild.id
        player: mafic.Player = interaction.guild.voice_client

        if not player:
            return await interaction.followup.send("I'm not connected to a voice channel.", ephemeral=True)

        if not player.current:
            return await interaction.followup.send("There is no current track.", ephemeral=True)

        embed = nextcord.Embed(
            title="Now Playing",
            color=nextcord.Color.green()
        )
        embed.set_thumbnail(url=player.current.artwork_url)
        embed.add_field(name="Track", value=player.current.title,inline=False)
        embed.add_field(name="Author", value=player.current.author,inline=False)
        embed.add_field(name='source',value=player.current.source,inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @nextcord.slash_command(name='volume',description='Change Volume')
    async def volume(self, interaction: nextcord.Interaction, *, volume: int):
        assert isinstance(interaction.user, nextcord.Member)
        await interaction.response.defer(ephemeral=True)

        guild_id = interaction.guild.id
        player: mafic.Player = interaction.guild.voice_client

        if not player:
            return await interaction.followup.send("I'm not connected to a voice channel.", ephemeral=True)

        if volume > 100:
            volume = 100
        elif volume < 0:
            volume = 0

        await player.set_volume(volume)
        embed = nextcord.Embed(
            title="Volume Set",
            description=f"**{volume}%** has been set.",
            color=nextcord.Color.green()
        )
        return await interaction.followup.send(embed=embed, ephemeral=True)

def setup(bot: commands.Bot):
    bot.add_cog(MusicCommands(bot))
    logger.info("Music commands cog loaded")
