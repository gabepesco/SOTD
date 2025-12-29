import os
import time
import datetime
from dotenv import load_dotenv
from faster_whisper import WhisperModel
# import whisperx
import discord
from discord.ext import commands, voice_recv

def transcribe_wav_file(wav_path):
    # Load the model only when needed
    model_size = "large-v3-turbo"
    device = "cuda"
    compute_type = "int8_float16"
    # whisper_model = whisperx.load_model(model_size, device=device, compute_type=compute_type)
    whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)
    # Extract base name without extension
    base_name = os.path.splitext(os.path.basename(wav_path))[0]
    transcript_path = f"transcriptions/{base_name}.txt"
    segments, info = whisper_model.transcribe(wav_path)
    transcript = ""
    for segment in segments:
        transcript += f"[{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}\n"
    with open(transcript_path, "w") as f:
        f.write(transcript)
    del whisper_model  # Explicitly delete to free VRAM

class WhisperBot(commands.Bot):
    def __init__(self, command_prefix):
        # Load environment variables
        load_dotenv()

        # Discord Bot Initialization
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix=command_prefix, intents=intents)

        # Discord variables
        self.DISCORD_TOKEN = str(os.getenv('DISCORD_TOKEN'))
        self.DISCORD_GUILD = int(os.getenv("DISCORD_GUILD")) # type: ignore
        self.BOT_CHANNEL_ID = int(os.getenv("BOT_CHANNEL_ID")) # type: ignore
        self.VOICE_CHANNEL_ID = int(os.getenv("VOICE_CHANNEL_ID")) # type: ignore

    async def on_ready(self):
        guild = self.get_guild(self.DISCORD_GUILD)
        assert isinstance(guild, discord.Guild), "Guild not found or invalid type"
        channel = guild.get_channel(self.VOICE_CHANNEL_ID)
        assert isinstance(channel, discord.VoiceChannel), "Channel not found or not VoiceChannel"
        self.guild = guild
        self.voice_channel = channel
    
    async def on_voice_state_update(self, member, before, after):
        # Only act if someone joins the target voice channel
        if after.channel and after.channel.id == self.VOICE_CHANNEL_ID:
            voice_client = discord.utils.get(self.voice_clients, guild=member.guild)
            if not voice_client:
                channel = after.channel
                voice_client = await channel.connect(cls=voice_recv.VoiceRecvClient)
                # Use ISO 8601 timestamp for file name
                join_time = datetime.datetime.now().isoformat(timespec="seconds").replace(":", "-")
                audio_path = f"audio/{join_time}.wav"
                self.audio_sink = voice_recv.WaveSink(audio_path)
                self.last_audio_file = audio_path  # Store last audio file path
                voice_client.listen(self.audio_sink)

        # If someone leaves the target voice channel, check if bot is alone
        if before.channel and before.channel.id == self.VOICE_CHANNEL_ID:
            channel = before.channel
            # Defensive: ensure self.user is set
            bot_user_id = getattr(self.user, 'id', None)
            non_bot_members = [m for m in channel.members if not m.bot or (bot_user_id is not None and m.id == bot_user_id)]
            if bot_user_id is not None and len(non_bot_members) == 1 and non_bot_members[0].id == bot_user_id:
                voice_client = discord.utils.get(self.voice_clients, guild=member.guild)
                if voice_client:
                    # Cleanup audio sink
                    if hasattr(self, 'audio_sink'):
                        self.audio_sink.cleanup()
                        del self.audio_sink
                    await voice_client.disconnect(force=True)
                    # Trigger transcription after leaving
                    if hasattr(self, 'last_audio_file') and os.path.exists(self.last_audio_file):
                        transcribe_wav_file(self.last_audio_file)

    async def on_audio_data(self, sink: voice_recv.AudioSink, user: discord.Member, data: bytes):
        # This is called when audio data is received
        timestamp = datetime.datetime.now().isoformat(timespec="seconds").replace(":", "-")
        filename = f"audio/{user.id}_{timestamp}.wav"
        with open(filename, "wb") as f:
            f.write(data)
        print(f"Saved audio for {user.display_name} to {filename}")
    
bot = WhisperBot(command_prefix="/")

# Start the bot
bot.run(bot.DISCORD_TOKEN)

# client.run(TOKEN) # type: ignore
