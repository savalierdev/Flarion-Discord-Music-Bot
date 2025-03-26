import nextcord
from nextcord.ext import commands
from loguru import logger
from settings import *

import mafic
from mafic import Player,TrackEndEvent,Track,TrackStartEvent,EndReason,NodeStats
from collections import defaultdict


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.nodes = mafic.NodePool(self.bot)
        self.ready_ran = False
        self.guild_queues = defaultdict(list)  # Dictionary to store queues per guild
        self.loop_modes = defaultdict(lambda: False)  # Dictionary to store loop mode per guild
        self.command_channels = {}  # Dictionary to store the channel where command was used per guild
        self.last_tracks = {}  # Dictionary to store last track per guild


    @commands.Cog.listener()
    async def on_node_ready(self, node: mafic.Node):
        logger.info(f"Lavalink node {node.label} is ready.")

    async def connect_node(self):
        if self.ready_ran:
            return

        await self.nodes.create_node(
            host=host,  # Lavalink server host
            port=port,  # Lavalink server port
            password=password,  # Lavalink server password
            secure=secure,  # Whether to use SSL
            label='main',  # Label for the node
        )

        self.ready_ran = True




    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()  # Wait until the bot is ready
        logger.info(f"Music cog is ready")
        await self.connect_node() # Connect to the Lavalink node when the bot is ready

    @nextcord.slash_command(name='join', description='Join a voice channel')
    async def join(self, interaction: nextcord.Interaction):
        assert isinstance(interaction.user, nextcord.Member)
        

        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
        
        chid = interaction.user.voice.channel

        await chid.connect(cls=mafic.Player)  # Connect to the voice channel
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
        await player.stop()  # Stop the player
        await player.disconnect()
        guild_id = interaction.guild.id
        self.guild_queues[guild_id].clear()  # Clear the queue for this guild
        self.loop_modes[guild_id] = False  # Reset loop mode for this guild


    @nextcord.slash_command(name='play', description='Play a song')
    async def play(self, interaction: nextcord.Interaction, *, query: str):
        await interaction.response.defer(ephemeral=True)
        assert isinstance(interaction.user, nextcord.Member)

        guild_id = interaction.guild.id
        self.command_channels[guild_id] = interaction.channel_id

        # Check if user is in a voice channel
        if not interaction.user.voice:
            embed = nextcord.Embed(
                title="Not in a Voice Channel",
                color=nextcord.Color.red()
            )
            embed.add_field(name="raise", value='You need to be in a voice channel to use this command.')
            return await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Connect to voice channel if not already connected
        player: mafic.Player = interaction.guild.voice_client
        if not player:
            try:
                player = await interaction.user.voice.channel.connect(cls=mafic.Player)
            except Exception as e:
                logger.error(f"Failed to connect: {e}")
        
        # Search for tracks
        try:
            tracks = await player.fetch_tracks(query,search_type='ytmsearch')
            if not tracks:
                embed = nextcord.Embed(
                    title="No Tracks Found",
                    color=nextcord.Color.red()
                )
                embed.add_field(name="Query", value='No tracks found for your query.')
                embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)
                return await interaction.followup.send(embed=embed, ephemeral=True)


            # If player is already playing, add to queue
            if player.current:
                if isinstance(tracks, mafic.Playlist):
                    # If it's a playlist, add all tracks except the first to the queue
                    embed = nextcord.Embed(
                        title="Playlist Added to Queue",
                        color=nextcord.Color.green()
                    )
                    embed.add_field(name='Playlist Name', value=tracks.name)
                    embed.add_field(name='Playlist Length', value=len(tracks.tracks))
                    embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    for track in tracks.tracks[1:]:
                        self.guild_queues[guild_id].append(track)
                else:
                    self.guild_queues[guild_id].append(tracks[0])
                    if tracks[0].identifier == player.current.identifier:
                        embed = nextcord.Embed(
                            title="Track Already Playing",
                            description=f"You Can't Add Same Track Again try instead /loop.",
                            color=nextcord.Color.red()
                        )
                        embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)
                        await interaction.followup.send(embed=embed, ephemeral=True)
                    embed = nextcord.Embed(
                        title="Track Added to Queue",
                        description=f"Added {tracks[0].title} to queue.",
                        color=nextcord.Color.green()
                    )
                    embed.set_thumbnail(url=tracks[0].artwork_url)
                    embed.add_field(name="Track", value=tracks[0].title,inline=False)
                    embed.add_field(name="Author", value=tracks[0].author,inline=False)
                    embed.add_field(name='source',value=tracks[0].source,inline=False)
                    embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)
                    await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                if isinstance(tracks, mafic.Playlist):
                    # If it's a playlist, play the first track and add the rest to the queue
                    await player.play(tracks.tracks[0])
                    self.guild_queues[guild_id].extend(tracks.tracks[1:])
                    embed = nextcord.Embed(
                        title="Playlist Added",
                        color=nextcord.Color.green()
                    )
                    embed.add_field(name='Playlist Name', value=tracks.name,inline=False)
                    embed.add_field(name='Playlist Length', value=len(tracks.tracks),inline=False)
                    embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    # Handle case where tracks is a list of Track objects
                    await player.play(tracks[0])
                    embed = nextcord.Embed(
                        title="Track",
                        color=nextcord.Color.green()
                    )
                    embed.set_thumbnail(url=tracks[0].artwork_url)
                    embed.add_field(name="Track", value=tracks[0].title,inline=False)
                    embed.add_field(name="Author", value=tracks[0].author,inline=False)
                    embed.add_field(name='source',value=tracks[0].source,inline=False)
                    embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)
                    await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error playing track: {e}")
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

    @nextcord.slash_command(name='loop', description='Toggle loop mode')
    async def loop(self, interaction: nextcord.Interaction, mode: str = nextcord.SlashOption(
        name="mode",
        description="Loop mode to set",
        choices={"Off": "off", "Track": "track", "Queue": "queue"},
        required=True
    )):
        assert isinstance(interaction.user, nextcord.Member)
        guild_id = interaction.guild.id

        # Check if user is in a voice channel
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
        
        # Check if bot is playing music
        player: mafic.Player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("I'm not playing any music.", ephemeral=True)

        if mode == "off":
            self.loop_modes[guild_id] = False
            await interaction.response.send_message("Loop mode disabled", ephemeral=True)
        elif mode == "track":
            self.loop_modes[guild_id] = "track"
            if player.current:
                self.last_tracks[guild_id] = player.current
            await interaction.response.send_message("Now looping current track", ephemeral=True)
        elif mode == "queue":
            self.loop_modes[guild_id] = "queue"
            if player.current:
                self.last_tracks[guild_id] = player.current
            await interaction.response.send_message("Now looping queue", ephemeral=True)



    @nextcord.slash_command(name='skip', description='Skip the current track')
    async def skip(self, interaction: nextcord.Interaction):
        await interaction.response.defer(ephemeral=True,with_message=True)
        assert isinstance(interaction.user, nextcord.Member)

        # Check if user is in a voice channel
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
        
        # Check if bot is playing music
        player: mafic.Player = interaction.guild.voice_client
        if not player or not player.current:
            return await interaction.response.send_message("I'm not playing any music.", ephemeral=True)
        
        # Save current track info for response
        current_track = player.current
        
        # Skip the current track
        try:
            await player.stop()
            embed = nextcord.Embed(
                title="Track Skipped",
                color=nextcord.Color.red()
            )
            embed.set_thumbnail(url=current_track.artwork_url)
            embed.add_field(name="Track", value=current_track.title,inline=False)
            embed.add_field(name="Author", value=current_track.author,inline=False)
            embed.add_field(name='source',value=current_track.source,inline=False)
            embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error skipping track: {e}")
            await interaction.followup.send(f"Error skipping track: {str(e)}", ephemeral=True)

    @nextcord.slash_command(name='queue', description='Show the current queue')
    async def queue(self, interaction: nextcord.Interaction):
        assert isinstance(interaction.user, nextcord.Member)
        guild_id = interaction.guild.id

        # Check if user is in a voice channel
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
        
        # Check if bot is playing music
        player: mafic.Player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("I'm not playing any music.", ephemeral=True)
        
        # Get the queue for this guild
        guild_queue = self.guild_queues[guild_id]
        
        # Show the current queue with pagination
        items_per_page = 10
        pages = (len(guild_queue) - 1) // items_per_page + 1 if guild_queue else 1

        class QueuePaginationView(nextcord.ui.View):
            def __init__(self, queue, current_track=None, timeout=60):
                super().__init__(timeout=timeout)
                self.queue = queue
                self.current_track = current_track
                self.current_page = 0
                self.items_per_page = items_per_page
                self.pages = pages
                
                # Disable Next button if only one page
                if pages <= 1:
                    self.children[1].disabled = True
                
            @nextcord.ui.button(label="Previous", style=nextcord.ButtonStyle.secondary, disabled=True)
            async def previous_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
                self.current_page -= 1
                if self.current_page == 0:
                    button.disabled = True
                self.children[1].disabled = False
                
                embed = self.create_embed()
                await interaction.response.edit_message(embed=embed, view=self)
                
            @nextcord.ui.button(label="Next", style=nextcord.ButtonStyle.secondary)
            async def next_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
                self.current_page += 1
                if self.current_page == self.pages - 1:
                    button.disabled = True
                self.children[0].disabled = False
                
                embed = self.create_embed()
                await interaction.response.edit_message(embed=embed, view=self)
                
            def create_embed(self):
                embed = nextcord.Embed(
                    title="Music Queue",
                    color=nextcord.Color.blue()
                )
                
                # Add currently playing track
                if self.current_track:
                    embed.add_field(
                        name="Currently Playing",
                        value=f"**{self.current_track.title}** - {self.current_track.author}",
                        inline=False
                    )
                
                # Add queue tracks for current page
                if self.queue:
                    start_idx = self.current_page * self.items_per_page
                    end_idx = min(start_idx + self.items_per_page, len(self.queue))
                    
                    queue_text = "\n".join([f"`{i+1}.` **{track.title}** - {track.author}" 
                                          for i, track in enumerate(self.queue[start_idx:end_idx], start=start_idx)])
                    
                    embed.add_field(
                        name="Up Next",
                        value=queue_text,
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Up Next",
                        value="No tracks in queue",
                        inline=False
                    )
                
                embed.set_footer(text=f"Page {self.current_page + 1}/{self.pages} | {len(self.queue)} tracks in queue")
                return embed

        if not guild_queue and not player:
            await interaction.response.send_message("The queue is empty and nothing is playing.", ephemeral=True)
        else:
            view = QueuePaginationView(guild_queue, player.current if player else None)
            await interaction.response.send_message(embed=view.create_embed(), view=view, ephemeral=True)

    @nextcord.slash_command(name='clear', description='Clear the current queue')
    async def clear(self, interaction: nextcord.Interaction):
        assert isinstance(interaction.user, nextcord.Member)
        guild_id = interaction.guild.id

        # Check if user is in a voice channel
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
        
        # Check if bot is playing music
        player: mafic.Player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("I'm not playing any music.", ephemeral=True)
        
        # Clear queuelist
        if self.guild_queues[guild_id]:
            self.guild_queues[guild_id].clear()
            embed = nextcord.Embed(
                title="Queue Cleared",
                description="The queue has been cleared.",
                color=nextcord.Color.red()
            )
            embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        await interaction.response.send_message("Cleared the queue.", ephemeral=True)

    @commands.Cog.listener()
    async def on_track_start(self,event:TrackStartEvent):
        assert isinstance(event.player, Player)
        assert isinstance(event.track, Track)
        guild_id = event.player.guild.id

        # Check if this is a looped track in track mode to avoid duplicate embeds
        if (self.loop_modes[guild_id] == "track" and 
            guild_id in self.last_tracks and 
            self.last_tracks[guild_id] and 
            self.last_tracks[guild_id].identifier == event.track.identifier):
            return
        self.last_tracks[guild_id] = event.track

        embed = nextcord.Embed(
            title="Now Playing",
            color=nextcord.Color.green()
        )
        embed.set_thumbnail(url=event.track.artwork_url)
        embed.add_field(name="Track", value=event.track.title,inline=False)
        embed.add_field(name="Author", value=event.track.author,inline=False)
        embed.add_field(name='source',value=event.track.source,inline=False)

        if guild_id in self.command_channels:
            channel = self.bot.get_channel(self.command_channels[guild_id])
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_track_end(self, event:TrackEndEvent):
        assert isinstance(event.player, Player)
        assert isinstance(event.track, Track)
        guild_id = event.player.guild.id

        # If Track Stopped and Track Loop is enabled skip next track
        if event.reason == EndReason.STOPPED:
            logger.info(f"Track stopped: {event.track.title}")
            if self.loop_modes[guild_id] == "track":
                if self.guild_queues[guild_id]:
                    next_track = self.guild_queues[guild_id].pop(0)
                    return await event.player.play(next_track)
                else:
                    embed = nextcord.Embed(
                        title="Queue Empty",
                        color=nextcord.Color.red()
                    )
                    embed.add_field(name='description', value='The queue is empty. Use /play to add more tracks.')
                    # send message to channel id
                    if guild_id in self.command_channels:
                        channel = self.bot.get_channel(self.command_channels[guild_id])
                        await channel.send(embed=embed)
                    return await event.player.disconnect()
            elif self.loop_modes[guild_id] == "queue":
                last_track = event.track
                self.guild_queues[guild_id].append(last_track)
                if self.guild_queues[guild_id]:
                    next_track = self.guild_queues[guild_id].pop(0)
                    await event.player.play(next_track)
                    logger.info(f"Playing next track: {next_track.title}")
            else:
                if self.guild_queues[guild_id]:
                    next_track = self.guild_queues[guild_id].pop(0)
                    await event.player.play(next_track)
                    logger.info(f"Playing next track: {next_track.title}")
                else:
                    embed = nextcord.Embed(
                        title="Queue Empty",
                        color=nextcord.Color.red()
                    )
                    embed.add_field(name='description', value='The queue is empty. Use /play to add more tracks.')
                    # send message to channel id
                    if guild_id in self.command_channels:
                        channel = self.bot.get_channel(self.command_channels[guild_id])
                        await channel.send(embed=embed)
                    return await event.player.disconnect()
                    

        if event.reason == EndReason.FINISHED:
            logger.info(f"Track finished: {event.track.title} - ")
            if self.loop_modes[guild_id] == "track":
                last_track = event.track
                return await event.player.play(last_track)
            elif self.loop_modes[guild_id] == "queue":
                last_track = event.track
                self.guild_queues[guild_id].append(last_track)
                if self.guild_queues[guild_id]:
                    next_track = self.guild_queues[guild_id].pop(0)
                    await event.player.play(next_track)
                    logger.info(f"Playing next track: {next_track.title}")
            else:
                if self.guild_queues[guild_id]:
                    next_track = self.guild_queues[guild_id].pop(0)
                    await event.player.play(next_track)
                    logger.info(f"Playing next track: {next_track.title}")
                else:
                    embed = nextcord.Embed(
                        title="Queue Empty",
                        color=nextcord.Color.red()
                    )
                    embed.add_field(name='description', value='The queue is empty. Use /play to add more tracks.')
                    # send message to channel id
                    if guild_id in self.command_channels:
                        channel = self.bot.get_channel(self.command_channels[guild_id])
                        await channel.send(embed=embed)
                    return await event.player.disconnect()

        if event.reason == EndReason.REPLACED:
            logger.info(f"Track replaced: {event.track.title}")

        # If there are tracks in the queue, play the next one


    @nextcord.slash_command(name='node', description='Get node info')
    async def node(self, interaction: nextcord.Interaction):
        assert isinstance(interaction.user, nextcord.Member)

        guild_id = interaction.guild.id

        # Check if user is in a voice channel
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
        
        # Check if bot is connected to a voice channel
        player: mafic.Player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("I'm not connected to a voice channel.", ephemeral=True)
        
        # Get node for guild id
        try:
            node = self.nodes.get_node(guild_id=guild_id,strategies=mafic.Strategy.SHARD)
        except Exception as e:
            logger.error(f"Error getting node: {e}")


def setup(bot: commands.Bot):
    bot.add_cog(Music(bot))
    logger.info("Music cog loaded")