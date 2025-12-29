
# class AudioSink(discord.sinks.RawDataSink):
#     """
#     Captures raw PCM16 audio from Discord and buffers it.
#     Once recording stops, dumps to WAV and runs Whisper.
#     """

#     def __init__(self):
#         super().__init__()
#         self.buffer = bytearray()

#     def write(self, user, data):
#         # data is already PCM16 48kHz mono—whisper is fine with 16–48 kHz
#         self.buffer.extend(data)

#     async def cleanup(self):
#         # Save buffer → WAV
#         sf.write("session.wav", 
#                  sf.frombuffer(bytes(self.buffer), dtype="int16")
#                    .reshape(-1, 1),
#                  48000)

#         # Transcribe
#         audio_input, _ = sf.read("session.wav")
#         inputs = processor(audio_input, sampling_rate=48000, return_tensors="pt")
#         input_ids = inputs["input_features"].to(model.device)

#         predicted_ids = model.generate(input_ids)
#         text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]

#         print("\n=== TRANSCRIPT ===")
#         print(text)
#         print("===================")


# @client.event
# async def on_message(message):
#     if message.author.bot:
#         return

#     if message.content == "!join":
#         if message.author.voice is None:
#             await message.channel.send("Join a voice channel first.")
#             return
#         # connect using the listening VoiceClient so listening methods are available
#         vc = await message.author.voice.channel.connect(cls=listening.VoiceClient)
#         await message.channel.send("Joined (listening-enabled).")
#         return

#     if message.content == "!record":
#         vc = message.guild.voice_client
#         if not vc:
#             await message.channel.send("Bot not in voice channel.")
#             return

#         # create a temporary directory to hold per-user PCM / converted WAVs
#         out_dir = tempfile.mkdtemp(prefix="dnd_record_")
#         # use AudioFileSink which writes raw pcm and exposes conversion helpers
#         sink = listening.AudioFileSink(directory=out_dir)  # directory arg for written files
#         # start listening; callback argument is optional
#         vc.listen(sink=sink)
#         await message.channel.send(f"Recording → {out_dir}")
#         # store sink reference on voice client so we can access it later
#         vc._listening_sink = sink
#         vc._listening_outdir = out_dir
#         return

#     if message.content == "!stop":
#         vc = message.guild.voice_client
#         if not vc or not getattr(vc, "_listening_sink", None):
#             await message.channel.send("Not currently recording.")
#             return

#         await message.channel.send("Stopping recording, converting and transcribing...")
#         # stop the listening session (this triggers sink.cleanup in the extension)
#         vc.stop_listening()

#         sink = vc._listening_sink
#         out_dir = vc._listening_outdir

#         # extension's AudioFileSink.cleanup should run and create WAVs; call cleanup to be sure.
#         # If the extension's API returns an awaitable cleanup, await it; otherwise call cleanup() synchronously.
#         try:
#             maybe = sink.cleanup()
#             if asyncio.iscoroutine(maybe):
#                 await maybe
#         except Exception:
#             # some versions may raise or not expose cleanup; ignore and proceed
#             pass

#         # now find WAVs in out_dir (the extension converts pcm->wav via ffmpeg)
#         wavs = sorted(glob.glob(os.path.join(out_dir, "**/*.wav"), recursive=True))
#         if not wavs:
#             # fallback: if pcm exists, convert to wav via soundfile (PCM is s16le 48k)
#             pcms = sorted(glob.glob(os.path.join(out_dir, "**/*.pcm"), recursive=True))
#             for pcm_path in pcms:
#                 wav_path = pcm_path + ".wav"
#                 # read raw int16 and write wav; adjust channels/samplerate if needed
#                 with open(pcm_path, "rb") as fh:
#                     raw = fh.read()
#                 import numpy as np
#                 arr = np.frombuffer(raw, dtype=np.int16)
#                 # Discord audio from sink is typically mono; if stereo adjust accordingly
#                 sf.write(wav_path, arr.astype("float32"), 48000)
#                 wavs.append(wav_path)

#         # transcribe each wav asynchronously (fire off tasks)
#         tasks = []
#         for w in wavs:
#             # try to infer username from filename pattern created by the sink (common: <user_id>.wav)
#             user_name = os.path.basename(w)
#             tasks.append(asyncio.create_task(transcribe_file(w, user_name=user_name)))

#         results = await asyncio.gather(*tasks, return_exceptions=True)
#         await message.channel.send(f"Transcription complete — {len([r for r in results if not isinstance(r, Exception)])} files processed.")
#         return

#     if message.content == "!leave":
#         vc = message.guild.voice_client
#         if vc:
#             await vc.disconnect()