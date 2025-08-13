import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel

model = WhisperModel("base", compute_type="int8")
def record(seconds=5, samplerate=16000):
    audio = sd.rec(int(seconds*samplerate), samplerate=samplerate, channels=1, dtype='float32')
    sd.wait()
    return audio.flatten()

def transcribe(seconds=5):
    audio = record(seconds)
    segments, _ = model.transcribe(audio, language="en")
    return " ".join(seg.text for seg in segments)

import asyncio, edge_tts
async def speak(text):
    tts = edge_tts.Communicate(text, voice="en-US-GuyNeural")
    await tts.stream()
