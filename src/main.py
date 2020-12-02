import aiocron
import discord
from datetime import datetime
from src import env
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os


# Discord Bot Initialization
TOKEN = env.DISCORD_TOKEN
GUILD = env.DISCORD_GUILD
intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)

# Spotify API Initialization
os.environ['SPOTIPY_REDIRECT_URI'] = env.SPOTIPY_REDIRECT_URI
os.environ['SPOTIPY_CLIENT_ID'] = env.SPOTIPY_CLIENT_ID
os.environ['SPOTIPY_CLIENT_SECRET'] = env.SPOTIPY_CLIENT_SECRET
auth_manager = SpotifyOAuth(scope='playlist-modify-private')
sp = spotipy.Spotify(auth_manager=auth_manager)


@aiocron.crontab("30 22 * * *")
async def notify():
    channel = client.get_channel(env.BOT_CHANNEL_ID)
    guild = discord.utils.find(lambda g: g.name == GUILD, client.guilds)

    day = datetime.today().weekday()
    user_id = env.DAY_UID_DICT[day]

    for member in guild.members:
        if member.id == user_id:
            user = member

    await channel.send(f'Hey {user.mention}, it\'s your song of the day!')


@client.event
async def on_message(message):
    # don't respond to ourselves
    #print(message.author, client.user)
    print("on_message")

    if "https://open.spotify.com/track/" in message.content and message.channel.id == env.BOT_CHANNEL_ID:
        words = str.split(message.content, " ")
        for word in words:
            if "https://open.spotify.com/track/" in word:
                url = word
        track_uri = "spotify:track:" + str.split(url, "?")[0][31:]
        playlist_uri = env.SPOTIFY_PLAYLIST_URI

        # add to playlist with spotify API
        sp.playlist_add_items(playlist_uri, [track_uri])
        await message.channel.send(f"Added {message.author}'s song to the playlist.")


@client.event
async def on_ready():
    guild = discord.utils.find(lambda g: g.name == GUILD, client.guilds)
    print(
        f'{client.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )

    notify.start()


client.run(TOKEN)
