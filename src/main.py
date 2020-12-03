import os
import discord
import spotipy
import aiocron
from datetime import datetime
from spotipy.oauth2 import SpotifyOAuth
from src.config import *


def main():
    # Discord Bot Initialization
    TOKEN = DISCORD_TOKEN
    GUILD = DISCORD_GUILD
    intents = discord.Intents.default()
    intents.members = True
    client = discord.Client(intents=intents)

    # Spotify API Initialization
    os.environ['SPOTIPY_REDIRECT_URI'] = SPOTIPY_REDIRECT_URI
    os.environ['SPOTIPY_CLIENT_ID'] = SPOTIPY_CLIENT_ID
    os.environ['SPOTIPY_CLIENT_SECRET'] = SPOTIPY_CLIENT_SECRET
    auth_manager = SpotifyOAuth(scope='playlist-modify-public')
    sp = spotipy.Spotify(auth_manager=auth_manager)

    @aiocron.crontab("00 22 * * *")
    async def notify():
        channel = client.get_channel(CHANNEL_ID)
        guild = discord.utils.find(lambda g: g.name == GUILD, client.guilds)

        day = datetime.today().weekday()
        user_id = DAY_UID_DICT[day]

        for member in guild.members:
            if member.id == user_id:
                user = member

        await channel.send(f'Hey {user.mention}, it\'s your song of the day!')
        print(f"Notified {user}.")

    @client.event
    async def on_message(message):
        print("on_message")
        if "https://open.spotify.com/track/" in message.content and message.channel.id == CHANNEL_ID:
            words = str.split(message.content, " ")
            for word in words:
                if "https://open.spotify.com/track/" in word:
                    url = word
            track_uri = "spotify:track:" + str.split(url, "?")[0][31:]
            playlist_uri = SPOTIFY_PLAYLIST_URI

            # add to playlist with spotify API
            sp.playlist_add_items(playlist_uri, [track_uri])
            await message.channel.send(f"Added {message.author}'s song to the playlist.")
            print(f"Added {message.author}'s song to the playlist.")

    @client.event
    async def on_ready():
        guild = discord.utils.find(lambda g: g.name == GUILD, client.guilds)
        print(f'{client.user} is connected to the following guild:\n'
              f'{guild.name}(id: {guild.id})')

        notify.start()

    client.run(TOKEN)


main()
