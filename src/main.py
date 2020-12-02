import discord
from discord.ext import tasks
from src import env

TOKEN = env.DISCORD_TOKEN
GUILD = env.DISCORD_GUILD

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)


@tasks.loop(seconds=5)
async def notify():
    channel = client.get_channel(env.CHANNEL_ID)
    guild = discord.utils.find(lambda g: g.name == GUILD, client.guilds)
    members = [member.name for member in guild.members]

    await channel.send(f"pinging SongOfTheDayBot")


@client.event
async def on_ready():
    guild = discord.utils.find(lambda g: g.name == GUILD, client.guilds)
    print(
        f'{client.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )

    notify.start()


client.run(TOKEN)
