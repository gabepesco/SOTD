import os
import time
import datetime
from dotenv import load_dotenv
import whisperx
from whisperx.diarize import DiarizationPipeline
import discord
from discord.ext import commands, voice_recv


def transcribe_wav_file(wav_path):
    # Load the model only when needed
    model_size = "large-v3-turbo"
    device = "cuda"
    compute_type = "int8_float16"
    batch_size = 16
    hf_token = os.getenv("HUGGINGFACE_TOKEN")

    # 1. Transcribe with whisperx
    model = whisperx.load_model(model_size, device, compute_type=compute_type)
    audio = whisperx.load_audio(wav_path)
    result = model.transcribe(audio, batch_size=batch_size)

    # 2. Align whisper output
    model_a, metadata = whisperx.load_align_model(
        language_code=result["language"], device=device
    )
    result = whisperx.align(
        result["segments"],
        model_a,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    )

    # 3. Speaker diarization
    diarize_model = DiarizationPipeline(use_auth_token=hf_token, device=device)
    diarize_segments = diarize_model(audio)
    result = whisperx.assign_word_speakers(diarize_segments, result)

    # Save diarized transcript
    base_name = os.path.splitext(os.path.basename(wav_path))[0]
    transcript_path = f"transcriptions/{base_name}.txt"
    with open(transcript_path, "w", encoding="utf-8") as f:
        for segment in result["segments"]:
            speaker = segment.get("speaker", "unknown")
            f.write(
                f"[Speaker {speaker}] [{segment['start']:.2f}s - {segment['end']:.2f}s] {segment['text']}\n"
            )

    # Cleanup
    del model
    del model_a
    del diarize_model
    import gc
    import torch

    gc.collect()
    torch.cuda.empty_cache()
    # Optionally remove the audio file after transcription
    # try:
    #     os.remove(wav_path)
    #     print(f"Removed audio file: {wav_path}")
    # except Exception as e:
    #     print(f"Failed to remove audio file {wav_path}: {e}")


class WhisperBot(commands.Bot):
    def __init__(self, command_prefix):
        # Load environment variables
        load_dotenv()

        # Discord Bot Initialization
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix=command_prefix, intents=intents)

        # Discord variables
        self.DISCORD_TOKEN = str(os.getenv("DISCORD_TOKEN"))
        self.DISCORD_GUILD = int(os.getenv("DISCORD_GUILD"))  # type: ignore
        self.BOT_CHANNEL_ID = int(os.getenv("BOT_CHANNEL_ID"))  # type: ignore
        self.VOICE_CHANNEL_ID = int(os.getenv("VOICE_CHANNEL_ID"))  # type: ignore

    async def on_ready(self):
        guild = self.get_guild(self.DISCORD_GUILD)
        assert isinstance(guild, discord.Guild), "Guild not found or invalid type"
        channel = guild.get_channel(self.VOICE_CHANNEL_ID)
        assert isinstance(
            channel, discord.VoiceChannel
        ), "Channel not found or not VoiceChannel"
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
                join_time = (
                    datetime.datetime.now()
                    .isoformat(timespec="seconds")
                    .replace(":", "-")
                )
                audio_path = f"audio/{join_time}.wav"
                self.audio_sink = voice_recv.WaveSink(audio_path)
                self.last_audio_file = audio_path  # Store last audio file path
                voice_client.listen(self.audio_sink)

        # If someone leaves the target voice channel, check if bot is alone
        if before.channel and before.channel.id == self.VOICE_CHANNEL_ID:
            channel = before.channel
            # Defensive: ensure self.user is set
            bot_user_id = getattr(self.user, "id", None)
            non_bot_members = [
                m
                for m in channel.members
                if not m.bot or (bot_user_id is not None and m.id == bot_user_id)
            ]
            if (
                bot_user_id is not None
                and len(non_bot_members) == 1
                and non_bot_members[0].id == bot_user_id
            ):
                voice_client = discord.utils.get(self.voice_clients, guild=member.guild)
                if voice_client:
                    # Cleanup audio sink
                    if hasattr(self, "audio_sink"):
                        self.audio_sink.cleanup()
                        del self.audio_sink
                    await voice_client.disconnect(force=True)
                    # Trigger transcription after leaving
                    if hasattr(self, "last_audio_file") and os.path.exists(
                        self.last_audio_file
                    ):
                        transcribe_wav_file(self.last_audio_file)

    async def on_audio_data(
        self, sink: voice_recv.AudioSink, user: discord.Member, data: bytes
    ):
        # This is called when audio data is received
        timestamp = (
            datetime.datetime.now().isoformat(timespec="seconds").replace(":", "-")
        )
        filename = f"audio/{user.id}_{timestamp}.wav"
        with open(filename, "wb") as f:
            f.write(data)
        print(f"Saved audio for {user.display_name} to {filename}")


bot = WhisperBot(command_prefix="/")

# Start the bot
bot.run(bot.DISCORD_TOKEN)

# client.run(TOKEN) # type: ignore
