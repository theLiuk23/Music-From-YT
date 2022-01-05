import discord
import os
import subprocess
from configparser import ConfigParser
from discord.ext import commands
from music import music_cog

# checks if ffmpeg is installed
try:
    subprocess.check_output(['which', 'ffmpeg'])
except:
    os.system('sudo apt install ffmpeg -y')

config = ConfigParser()
config.read('variables.ini')
prefix = config.get('variables', 'prefix')

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

client = commands.Bot(command_prefix=prefix, intents=intents)
client.add_cog(music_cog(client))

token = config.get('variables', 'token')
client.run(token, bot=True)