import os
import discord
import spotipy
import aiocron
from datetime import datetime
from spotipy.oauth2 import SpotifyOAuth
import config


def main():
    # Discord Bot Initialization
    TOKEN = config.DISCORD_TOKEN
    GUILD = config.DISCORD_GUILD
    intents = discord.Intents.default()
    intents.members = True
    client = discord.Client(intents=intents)

    # Spotify API Initialization
    os.environ['SPOTIPY_REDIRECT_URI'] = config.SPOTIPY_REDIRECT_URI
    os.environ['SPOTIPY_CLIENT_ID'] = config.SPOTIPY_CLIENT_ID
    os.environ['SPOTIPY_CLIENT_SECRET'] = config.SPOTIPY_CLIENT_SECRET
    auth_manager = SpotifyOAuth(scope='playlist-modify-public')
    sp = spotipy.Spotify(auth_manager=auth_manager)

    # This function notifies people at 22:00 that it is their day.
    @aiocron.crontab("10 22 * * *")
    async def notify():
        channel = client.get_channel(config.CHANNEL_ID)
        guild = discord.utils.find(lambda g: g.name == GUILD, client.guilds)

        day = datetime.today().weekday()
        user_id = config.DAY_UID_DICT[day]

        for member in guild.members:
            if member.id == user_id:
                user = member

        await channel.send(f'Hey {user.mention}, it\'s your song of the day!')
        print(f'Notified {user} on day {day}.')

    @client.event
    async def on_message(message):
        if 'https://open.spotify.com/track/' in message.content and message.channel.id == config.CHANNEL_ID:
            words = str.split(message.content, " ")
            for word in words:
                if 'https://open.spotify.com/track/' in word:
                    url = word
                    break

            # format URIs for spotify's API
            track_id = str.split(url, "?")[0][31:]
            track_uri = f'spotify:track:{track_id}'
            playlist_uri = config.SPOTIFY_PLAYLIST_URI

            # add to playlist with spotify API
            sp.playlist_add_items(playlist_uri, [track_uri])
            await message.channel.send(f'Added {message.author}\'s song to the playlist.')
            print(f'Added {message.author}\'s song to the playlist.')

    @client.event
    async def on_ready():
        guild = discord.utils.find(lambda g: g.name == GUILD, client.guilds)
        print(f'{client.user} is connected to the following guild:\n'
              f'{guild.name}(id: {guild.id})')

        notify.start()

    client.run(TOKEN)


main()
