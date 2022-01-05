import re
from lyricsgenius import genius
from youtube_dl import YoutubeDL
from configparser import ConfigParser
from datetime import datetime
from discord.ext import commands
from re import T

import discord as ds
import lyricsgenius
import aiohttp
import asyncio
import time
import os


class music_cog(commands.Cog):
    def __init__(self, bot):
        self.FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        self.YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist':'True', 'quiet':'True'}
        self.lyrics_url = "https://some-random-api.ml/lyrics?title="
        self.lyrics_token = 'Bxj4Q8XhvQzCkDxXqmEm_lfCNbEeXaqTvDVISdHUaPCz3pcYJ7YD85A3KyzVQ7VW'
        self.is_playing = False
        self.music_queue = []
        self.now_playing = ""
        self.voice_channel = ""
        self.last_song_info = ""
        self.music_position = 0
        self.my_volume = 1.0
        self.now = ""
        self.bot = bot


    # gets a dictionary with all the info from the requested song
    def search_on_yt(self, item):
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info("ytsearch:%s" % item, download=False)['entries'][0]
            except Exception:
                return False
        return {'source': info['formats'][0]['url'], 'title': info['title'], 'duration': info['duration'], 'channel': info['channel']}


    async def disconnect_bot(self, ctx, reason):
        bot_channel = ctx.guild.voice_client
        if bot_channel is not None:
            self.voice_channel = ""
            self.music_queue = []
            # if requested from the user...
            if reason == "command":
                await ctx.send("You disconnected me?!?! How dare you?")
            await bot_channel.disconnect()
        else:
            await ctx.send("I can\'t disconnect from anything. KEKW")


    # creates a loop for the music queue:
    #   runs play_next after song ended up
    async def async_lambda(self, ctx):
        coroutine = self.play_next(ctx)
        future = asyncio.run_coroutine_threadsafe(coroutine, self.bot.loop)
        try:
            future.result()
        except Exception as e:
            await ctx.send('Error while starting to play next song.')
            print(e)


    # plays next song
    # aka "skip"
    def play_next(self, ctx):
        if len(self.music_queue) > 0:
            self.is_playing = True
            mp3_url = self.music_queue[0][0]['source']
            if str(ctx.author.voice.channel) != str(self.music_queue[0][1]):
                self.voice_channel = self.bot.move_to(self.music_queue[0][1])
            self.now_playing = self.music_queue[0][0]
            self.music_queue.pop(0)
            if not self.voice_channel.is_playing():
                self.voice_channel.play(ds.FFmpegPCMAudio(mp3_url, **self.FFMPEG_OPTIONS), after = lambda e: self.play_next(ctx))
                self.voice_channel.source = ds.PCMVolumeTransformer(self.voice_channel.source, volume=self.my_volume)
                self.music_position = (datetime.now() - datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
                return 0
            else:
                return -1
        elif len(self.music_queue) <= 0:
            self.is_playing = False
            if self.voice_channel == "":
                return 1
            if not self.voice_channel.is_playing():
                asyncio.run_coroutine_threadsafe(self.disconnect_bot(ctx, "bot"), self.bot.loop)
                return 0
        else:
            ctx.send('I think the music queue is empty... not good!')
            return 1


    # aka "play" for first time
    # runs only if self.is_playing == false
    async def play_music(self, ctx):
        try:
            if len(self.music_queue) > 0:
                mp3_url = self.music_queue[0][0]['source']
                if (self.voice_channel == "" or not self.voice_channel.is_connected()):
                    self.voice_channel = await self.music_queue[0][1].connect()
                elif str(ctx.author.voice.channel) != str(self.music_queue[0][1]):
                    self.voice_channel = await self.bot.move_to(self.music_queue[0][1])
                self.now_playing = self.music_queue[0][0]
                self.music_queue.pop(0)
                self.voice_channel.play(ds.FFmpegPCMAudio(mp3_url, **self.FFMPEG_OPTIONS), after = lambda e: self.play_next(ctx))
                self.voice_channel.source = ds.PCMVolumeTransformer(self.voice_channel.source, volume=self.my_volume)
                self.music_position = (datetime.now() - datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
                self.is_playing = True
            else:
                # runs if the last song has been skipped
                self.is_playing = False
        except ds.ClientException as e:
            print(e)
            print(e.args)
            print(e.with_traceback())
            await ctx.send('Holy maccaroni, something went wrong over there. Try again.')


    # adds a song to the queue
    async def add_song(self, ctx, *args):
        query = "".join(args)
        if ctx.author.voice is not None:
            user_channel = ctx.author.voice.channel
            self.song_info = self.search_on_yt(query)
            if type(self.song_info) == type(True):
                await ctx.send("Could not download the song. Try another keyword. Probably I found a playlist or a livestream.")
            else:
                self.music_queue.append([self.song_info, user_channel])
                title = self.song_info['title']
                await ctx.send(f'"{title}" added to the queue!')
                if self.is_playing == False:
                    await self.play_music(ctx)
        else:
            await ctx.send("Connect to a voice channel.")
            return


    # runs at script startup
    @commands.Cog.listener()
    async def on_ready(self):
        self.variables()
        # writes in ini file the pid of this script
        pid = str(os.getppid())
        config = ConfigParser()
        config.read('variables.ini')
        config.set('variables', 'pid', pid)
        configfile = open("variables.ini", 'w')
        config.write(configfile)
        configfile.close()
        # Bot finally online
        print(f"BOT IS NOW ONLINE with pid: {pid}!")
        channel = self.bot.get_channel(750726532317577328)
        prefix = config.get('variables', 'prefix')
        await channel.send(f'It\'s {self.now}\nMusic on YT! is finally online.\nType "{prefix}wtf" to have a list of the avaible commands.')


    @commands.Cog.listener()
    async def on_command_error(error, ctx, *args):
        config = ConfigParser()
        config.read('variables.ini')
        prefix = config.get('variables', 'prefix')
        if type(args[0]) == commands.CommandNotFound:
            await ctx.send(f"This command is not avaible. Type {prefix}wtf to get a list of the avaible commands.")
        elif type(args[0]) == commands.DisabledCommand:
            await ctx.send("This command has been disabled. Call Liuk23 #3966 to have more information.")
        elif type(args[0]) == commands.CommandOnCooldown:
            await ctx.send("Chill bro. Write more slowly!")
        else:
            await ctx.send("Unexpected error. Are you sure you wrote the command correctly?")
        # print(f'{error};\n{args}')


    # loads some variables before doing any task
    def variables(self):
        self.now  = datetime.now().strftime("%d/%m/%Y %H:%M:%S")


    @commands.command(name="pause")
    async def pause(self, ctx):
        self.variables()
        voice = ds.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice.is_playing():
            voice.pause()
            await ctx.send("Song paused")
        else:
            await ctx.send("There is no song playing at the moment")

    
    @commands.command(name="resume")
    async def resume(self, ctx):
        self.variables()
        voice = ds.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice.is_paused():
            voice.resume()
            await ctx.send("Starting to play again")
        else:
            await ctx.send("There  is no song paused at the moment")

    
    @commands.cooldown(1, 5, commands.BucketType.guild)
    @commands.command(name="play")
    async def play(self, ctx, *args):
        self.variables()
        print(str(self.now) + " - " + str(ctx.author) + " added \"" + str(ctx.message.content[6:]) + "\" to the queue.")
        await self.add_song(ctx, *args)


    @commands.command(name="next")
    async def next(self, ctx):
        self.variables()
        print(str(self.now) + " - " + str(ctx.author) + " looked for the next song in the queue.")
        message = "Here's the music queue:\n"
        index = 1
        for i in range(0, len(self.music_queue)):
            message += str(index) + " - " + self.music_queue[i][0]['title'] + "\n"
            index = index + 1
        if message != "":
            await ctx.send(message)
        else:
            await ctx.send("No music in queue.")


    @commands.command(name="lyrics")
    async def lyrics(self, ctx):
        self.variables()
        try:
            message = ctx.message.content
            config = ConfigParser()
            config.read('variables.ini')
            prefix = config.get('variables', 'prefix')
            arg = message.replace(prefix + 'lyrics ', '')
            arg = message.replace(prefix + 'lyrics', '')
            if self.now_playing != "":
                if arg == '':
                    arg = self.now_playing['title']
            else:
                await ctx.send("I'm playing nothing atm, dude!")
            print(str(self.now) + " - " + str(ctx.author) + " asked for '" + str(arg) +  "' lyrics.")
            g = lyricsgenius.Genius(self.lyrics_token)
            song = g.search_song(arg)
            if song is None:
                await ctx.send(f'I couldn\'t find lyrics. Try to specify the title of the song: {prefix}lyrics [title]')
                return
            lyrics = song.lyrics
            author = song.artist
            title = song.title
            image = song.song_art_image_url
            embed = ds.Embed(title=title)
            embed.set_author(name=author)
            embed.description = f'*Requsted by {ctx.author.display_name}'
            if len(lyrics) >= 2048:
                embed.add_field(name='Link', value=f'Lyrics are too long for discord embeds . Here\'s a link, my dude:\n{song.url}') 
            else:
                embed.set_footer(text=lyrics)
            embed.set_image(url=image)
            await ctx.send(embed=embed)
        except Exception as e:
            print(e)


    @commands.command(name="np")
    async def np(self, ctx):
        self.variables()
        print(str(self.now) + " - " + str(ctx.author) + " looked for the current playing song.")
        if self.voice_channel == "":
            await ctx.send('I\'m not connected to a voice channel atm ==> i\'m playing nothing!')
            return      
        if not self.voice_channel.is_playing():
            await ctx.send("I'm playing nothing atm, dude. Aw, what a shame...")
            return
        try:
            track = self.now_playing
            duration_sec = track['duration']
            music_position = (datetime.now() - datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds() - self.music_position
            embed = ds.Embed(title="Now playing")
            embed.set_author(name="Playback Info")
            embed.set_footer(text=f'*Requsted by {ctx.author.display_name}')
            embed.add_field(name="Track title", value=track['title'], inline=False)
            embed.add_field(name="Channel", value=track['channel'], inline=False)
            embed.add_field(name="Duration", value=str(int(duration_sec / 60)) + " minutes and " + str(int(duration_sec % 60)) + " seconds.", inline=False)
            embed.add_field(name="Already played", value=(str(int(music_position / 60)) + " minutes and " + str(int(music_position % 60)) + " seconds. (" + str(round(music_position / duration_sec * 100, 2)) + "%)"), inline=False)
        except Exception as e:
            print(e)
            return
        await ctx.send(embed=embed)


    @commands.command(name="skip")
    async def skip(self, ctx):
        self.variables()
        print(str(self.now) + " - " + str(ctx.author) + " skipped a song.")
        if self.voice_channel != "":
            self.voice_channel.stop()
            await ctx.send("You didn't like this song? Np, i'm playing the next one!")
            error = self.play_next(ctx)
            if error == -1:
                await ctx.send('i\'m already playing something')


    @commands.command(name="stop")
    async def stop(self, ctx):
        self.variables()
        await self.disconnect_bot(ctx, "command")

    
    @commands.command(name="offline")
    async def offline(self, ctx):
        # gets the role by name
        role = ds.utils.find(lambda r: r.name == 'Consul', ctx.message.guild.roles)
        if not role in ctx.author.roles:
            await ctx.send('Hey man, you need to be a "Consul" to offline me!')
            return
        config = ConfigParser()
        config.read('variables.ini')
        config.set('variables', 'pid', 'null')
        configfile = open('variables.ini', 'w')
        config.write(configfile)
        configfile.close()
        self.variables()
        print(str(self.now) + " - " + str(ctx.author) + " offlined the bot.")
        bot_channel = ctx.guild.voice_client
        if bot_channel is not None:
            await self.disconnect_bot(ctx, "command")
        await ctx.send("Bot is now offline. See ya next time!")
        await self.bot.close()
        
    
    @commands.command(name="volume")
    async def volume(self, ctx, volume: int = None):
        self.variables()
        if volume == None:
            await ctx.send("The volume is currently set to: " + str(int(self.my_volume * 100)) + "%")
            print(str(self.now) + " - " + str(ctx.author) + " wanted to know the current volume")
            return
        float_volume = float(volume / 100)
        if volume > 200 or volume < 0:
            await ctx.send("Volume must be between 0 and 200.")
            return
        self.voice_channel.source.volume = float_volume
        self.my_volume = float_volume
        print(str(self.now) + " - " + str(ctx.author) + " changed the volume to " + str(float_volume * 100) + "%")
        await ctx.send("Volume changed to " + str(int(self.voice_channel.source.volume * 100)) + "%")


    @commands.command(name="wtf")
    async def wtf(self, ctx):
        self.variables()
        print(str(self.now) + " - " + str(ctx.author) + " asked for some help.")
        config = ConfigParser()
        config.read('variables.ini')
        prefix = config.get('variables', 'prefix')
        text = 'Here\'s a list of the avaible commands:\n'
        avaible_commands = [
        "play --> It plays a song from youtube in to your voice channel (argument needed)",
        "next --> It tells the user which are the next songs",
        "np --> It tells the user which song is currently playing",
        "offline --> It offlines the bot (Consul role required)",
        "pause --> It pauses the current playing song (bot will reload)",
        "prefix --> It changes the prefix of the bot",
        "resume --> It starts playing the song where it was paused",
        f"lyrics --> It shows the lyrics of the current playing song (type '{prefix}lyrics [title]' if the bot does not found lyrics automatically)",
        "stop --> It disconnects the bot from the voice channel",
        "skip --> It plays the next song in the queue",
        "volume --> It gets or sets the volume of the playing song (it must be between 0 and 200)",
        ]
        count = 1
        for command in avaible_commands:
            text += str(count) + " - " + command + "\n"
            count += 1
        await ctx.send(text)


    @commands.command(name="prefix")
    async def prefix(self, ctx):
        self.variables()
        try:
            message = ctx.message.content.split(' ')
            if len(message) == 1:
                await ctx.send('You didn\'t specified the new prefix.')
                return
            prefix = message[1]
            if len(prefix) != 1:
                print(len(prefix))
                await ctx.send('Prefix must be a single character.')
                return
            config = ConfigParser()
            config.read('variables.ini')
            if prefix == config.get('variables', 'prefix'):
                await ctx.send(f'"{prefix}" is already the current prefix.')
                return
            print(str(self.now) + " - " + str(ctx.author) + " changed the prefix to " + prefix)
            config.set('variables', 'prefix', prefix)
            configfile = open("variables.ini", 'w')
            config.write(configfile)
            configfile.close()
            await ctx.send(f'Prefix successfully changed to "{prefix}". Wait few seconds the bot to restart.')
            print(str(self.now) + " - " + str(ctx.author) + " changed the prefix to " + str(prefix))
            os.system('python3 start.py')
        except Exception as e:
            print(e)
            await ctx.send('Couldn\'t changed the prefix.')
            return