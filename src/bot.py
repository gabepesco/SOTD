# bot.py
import os
import discord
import spotipy
from aiocron import crontab
from datetime import datetime
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv


def main():
    # load env variables
    load_dotenv()

    # Discord Bot Initialization
    token = os.getenv('DISCORD_TOKEN')
    intents = discord.Intents.default()
    intents.members = True
    client = discord.Client(intents=intents)

    # Spotify API Initialization
    # Since we named the spotify environment variables correctly in the .env file,
    # we don't need to set them again with os.environ['...'].

    auth_manager = SpotifyOAuth(scope='playlist-modify-public')
    sp = spotipy.Spotify(auth_manager=auth_manager)

    def get_user_of_the_day():
        guild = discord.utils.find(lambda g: g.name == os.getenv('DISCORD_GUILD'), client.guilds)

        day = datetime.today().weekday()
        user_id = eval(os.getenv('DAY_USERID_DICT'))[day]

        for member in guild.members:
            if member.id == user_id:
                user = member

        return user

    @crontab("00 12 * * *")
    async def notify():
        # This function notifies people at 22:00 that it is their day.
        channel_id = int(os.getenv('CHANNEL_ID'))
        channel = client.get_channel(channel_id)
        user = get_user_of_the_day()
        if not eval(os.getenv('ADDED_SONG')):
            await channel.send(f'Hey {user}, it\'s your song of the day!')

    @crontab("45 23 * * *")
    async def late_notify():
        # This function pings people at 23:45 that it is their day.

        channel_id = int(os.getenv('CHANNEL_ID'))
        channel = client.get_channel(channel_id)
        user = get_user_of_the_day()

        if not eval(os.getenv('ADDED_SONG')):
            await channel.send(f'Hey {user.mention}, you only have 15 more minutes to add a song.')

    @crontab('01 00 * * *')
    async def reset_added_song():
        os.environ['ADDED_SONG'] = "False"

        channel_id = int(os.getenv('CHANNEL_ID'))
        channel = client.get_channel(channel_id)
        await channel.purge(check=lambda m: m.author == client.user)

    def get_uri_from_message(url):
        words = str.split(url, " ")
        for word in words:
            if 'https://open.spotify.com/track/' in word:
                url = word
                break

        # format URIs for spotify's API
        track_id = str.split(url, "?")[0][31:]
        track_uri = f'spotify:track:{track_id}'
        return track_uri

    @client.event
    async def on_message(message):
        channel_id = int(os.getenv('CHANNEL_ID'))
        if 'https://open.spotify.com/track/' in message.content and message.channel.id == channel_id:
            track_uri = get_uri_from_message(message.content)
            playlist_uri = os.getenv('SPOTIFY_PLAYLIST_URI')

            tracks = sp.playlist_items(playlist_id=playlist_uri, fields='items.track.id', limit=100)
            playlist_tracks = set(i['track']['id'] for i in tracks['items'])
            string = track_uri.split(":")[2]

            if string not in playlist_tracks:
                # add to playlist with spotify API
                sp.playlist_add_items(playlist_uri, [track_uri])
                os.environ['ADDED_SONG'] = "True"
                await message.add_reaction('👍')
            else:
                await message.channel.send(f'{message.user.mention}: The song was not added, it is already in the playlist.')

    @client.event
    async def on_ready():
        guild = discord.utils.find(lambda g: g.name == os.getenv('DISCORD_GUILD'), client.guilds)
        print(f'{client.user} is connected to the following guild:\n'
              f'{guild.name}(id: {guild.id})')

        # notify.start()
        late_notify.start()
        reset_added_song.start()

    client.run(token)


main()
