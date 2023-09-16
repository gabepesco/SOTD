import os
import discord
import spotipy
from aiocron import crontab
from datetime import datetime
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from discord.ext import commands


class SOTDBot(commands.Bot):
    def __init__(self, command_prefix):
        super().__init__(command_prefix)
        self.added_song = {}

        # Load environment variables
        load_dotenv()

        # Discord Bot Initialization
        self.token = os.getenv('DISCORD_TOKEN')
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix=command_prefix, intents=intents)

        # Discord variables
        self.discord_guild = os.getenv('DISCORD_GUILD')
        self.channel_id = int(os.getenv('CHANNEL_ID'))
        self.spotify_playlist_uri = os.getenv('SPOTIFY_PLAYLIST_URI')
        self.day_userid_dict = eval(os.getenv('DAY_USERID_DICT'))

        # Spotify API Initialization
        auth_manager = SpotifyOAuth(scope='playlist-modify-public')
        self.sp = spotipy.Spotify(auth_manager=auth_manager)

        # Crontab scheduling functions
        crontab('00 11 * * *', func=self.notify)
        crontab("00 23 * * *", func=self.late_notify)
        crontab("01 00 * * *", func=self.reset_added_song)

    def get_users_of_the_day(self):
        guild = discord.utils.find(lambda g: g.name == self.discord_guild, self.guilds)

        day = datetime.today().weekday()
        user_ids = self.day_userid_dict[day]

        return [member for member in guild.members if member.id in user_ids]

    async def notify(self):
      # This function notifies people at 11:00 that it is their day.
      channel = self.get_channel(self.channel_id)

      for user, added in self.added_song.items():
        if not added:
          await channel.send(f'Hey {user.nick}, it\'s your song of the day!')

    async def late_notify(self):
        # This function pings people at 23:00 that they have one hour left to add a song.
        channel = self.get_channel(self.channel_id)

        for user, added in self.added_song.items():
            if not added:
                await channel.send(f'Hey {user.mention}, you have an hour left to add a song.')

    async def reset_added_song(self):
        self.added_song = {user: False for user in self.get_users_of_the_day()}

        channel = self.get_channel(self.channel_id)
        await channel.purge(check=lambda m: m.author == self.user)

    @staticmethod
    def get_uri_from_message(url):
        words = str.split(url, " ")
        for word in words:
            if 'https://open.spotify.com/track/' in word:
                url = word
                break

        # format URIs for Spotify's API
        track_id = str.split(url, "?")[0][31:]
        track_uri = f'spotify:track:{track_id}'
        return track_uri

    def fetch_playlist_tracks(self):
        offset = 0
        tracks = []

        while True:
            playlist_items = self.sp.playlist_items(
                playlist_id=self.spotify_playlist_uri,
                fields='items.track.id',
                limit=100,
                offset=offset,
                additional_types=('track',)
            )['items']

            tracks.extend(playlist_items)

            if len(playlist_items) < 100:
                break

            offset += 100

        return [track['track']['id'] for track in tracks]

    async def on_message(self, message):
        if message.author == self.user:
            return

        if 'https://open.spotify.com/track/' in message.content and message.channel.id == self.channel_id:
            track_uri = self.get_uri_from_message(message.content)

            playlist_tracks = self.fetch_playlist_tracks()
            track_id = track_uri.split(":")[2]

            if track_id not in playlist_tracks:
                self.sp.playlist_add_items(self.spotify_playlist_uri, [track_uri])
                self.added_song[message.author] = True
                await message.add_reaction('👍')
            else:
                await message.channel.send(f'{message.author.mention}: The song was not added, it is already in the playlist.')

    async def on_ready(self):
        guild = discord.utils.find(lambda g: g.name == self.discord_guild, self.guilds)
        print(f'{self.user} is connected to the following guild:\n{guild.name}(id: {guild.id})')

        self.added_song = {user: False for user in self.get_users_of_the_day()}
        print(f'added_song: {self.added_song}')


# Create an instance of the SOTDBot class
# bot = SOTDBot(command_prefix='!')
bot = SOTDBot(command_prefix=None)

# Start the bot
bot.run(bot.token)
