# bot.py
import os
import discord
import spotipy
from aiocron import crontab
from datetime import datetime
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

global added_song


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

    def get_users_of_the_day():
        guild = discord.utils.find(lambda g: g.name == os.getenv('DISCORD_GUILD'), client.guilds)

        day = datetime.today().weekday()
        user_ids = eval(os.getenv('DAY_USERID_DICT'))[day]

        return [member for member in guild.members if member.id in user_ids]

    @crontab("00 11 * * *")
    async def notify():
        # This function notifies people at 11:00 that it is their day.
        channel_id = int(os.getenv('CHANNEL_ID'))
        channel = client.get_channel(channel_id)

        for user, added in added_song.items():
            if not added:
                await channel.send(f'Hey {user.nick}, it\'s your song of the day!')

    @crontab("00 23 * * *")
    async def late_notify():
        # This function pings people at 23:00 that they have one hour left to add a song.
        channel_id = int(os.getenv('CHANNEL_ID'))
        channel = client.get_channel(channel_id)

        for user, added in added_song.items():
            if not added:
                await channel.send(f'Hey {user.mention}, you have an hour left to add a song.')

    @crontab('01 00 * * *')
    async def reset_added_song():
        global added_song
        added_song = {user: False for user in get_users_of_the_day()}

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
        global added_song
        channel_id = int(os.getenv('CHANNEL_ID'))

        if 'https://open.spotify.com/track/' in message.content and message.channel.id == channel_id:
            track_uri = get_uri_from_message(message.content)
            playlist_uri = os.getenv('SPOTIFY_PLAYLIST_URI')

            i = 1
            offset = 0

            tracks = sp.playlist_items(
                playlist_id=playlist_uri,
                fields='items.track.id',
                limit=100,
                offset=offset,
                additional_types=('track',)
            )['items']

            while len(tracks) == i * 100:
                i += 1
                offset += 100
                tracks += sp.playlist_items(
                    playlist_id=playlist_uri,
                    fields='items.track.id',
                    limit=100,
                    offset=offset,
                    additional_types=('track',)
                )['items']

            playlist_tracks = {i['track']['id'] for i in tracks}
            string = track_uri.split(":")[2]

            if string not in playlist_tracks:
                if message.author in added_song:
                    if not added_song[message.author]:
                        # add to playlist with spotify API
                        sp.playlist_add_items(playlist_uri, [track_uri])
                        added_song[message.author] = True
                        await message.add_reaction('👍')
                    else:
                        await message.channel.send(f'{message.author.mention}: Woah there pardner, you best watch yourself. I got my eye on you.')
                else:
                    # add to playlist with spotify API
                    sp.playlist_add_items(playlist_uri, [track_uri])
                    added_song[message.author] = True
                    await message.add_reaction('👍')
            else:
                await message.channel.send(f'{message.author.mention}: The song was not added, it is already in the playlist.')

    @client.event
    async def on_ready():
        guild = discord.utils.find(lambda g: g.name == os.getenv('DISCORD_GUILD'), client.guilds)
        print(f'{client.user} is connected to the following guild:\n{guild.name}(id: {guild.id})')

        global added_song
        added_song = {user: False for user in get_users_of_the_day()}

    client.run(token)


main()
