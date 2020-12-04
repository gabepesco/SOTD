# bot.py
import os
import discord
import spotipy
from aiocron import crontab
from datetime import datetime
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv


def main():
    # get variables
    load_dotenv()

    # Discord Bot Initialization
    token = os.getenv('DISCORD_TOKEN')
    intents = discord.Intents.default()
    intents.members = True
    client = discord.Client(intents=intents)

    # Spotify API Initialization
    # Since we named the spotify environment variables correctly in the .env file,
    # we don't need to set them again in the environment.

    auth_manager = SpotifyOAuth(scope='playlist-modify-public')
    sp = spotipy.Spotify(auth_manager=auth_manager)

    # This function notifies people at 22:00 that it is their day.
    @crontab("00 22 * * *")
    async def notify():
        channel_id = int(os.getenv('CHANNEL_ID'))
        channel = client.get_channel(channel_id)

        guild = discord.utils.find(lambda g: g.name == os.getenv('DISCORD_GUILD'), client.guilds)

        day = datetime.today().weekday()
        user_id = eval(os.getenv('DAY_USERID_DICT'))[day]

        for member in guild.members:
            if member.id == user_id:
                user = member

        await channel.send(f'Hey {user.mention}, it\'s your song of the day!')
        print(f'Notified {user} on day {day}.')

    @client.event
    async def on_message(message):
        channel_id = int(os.getenv('CHANNEL_ID'))

        if 'https://open.spotify.com/track/' in message.content and message.channel.id == channel_id:
            words = str.split(message.content, " ")
            for word in words:
                if 'https://open.spotify.com/track/' in word:
                    url = word
                    break

            # format URIs for spotify's API
            track_id = str.split(url, "?")[0][31:]
            track_uri = f'spotify:track:{track_id}'
            playlist_uri = os.getenv('SPOTIFY_PLAYLIST_URI')

            # add to playlist with spotify API
            sp.playlist_add_items(playlist_uri, [track_uri])
            await message.channel.send(f'Added {message.author}\'s song to the playlist.')
            print(f'Added {message.author}\'s song to the playlist.')

    @client.event
    async def on_ready():
        guild = discord.utils.find(lambda g: g.name == os.getenv('DISCORD_GUILD'), client.guilds)
        print(f'{client.user} is connected to the following guild:\n'
              f'{guild.name}(id: {guild.id})')

        notify.start()

    client.run(token)


main()
