import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
import asyncio, edge_tts

_sr = 16000
_model = WhisperModel("base", compute_type="int8")

def record(seconds=5, samplerate=_sr):
    audio = sd.rec(int(seconds*samplerate), samplerate=samplerate, channels=1, dtype='float32')
    sd.wait()
    return audio.flatten()

def transcribe(seconds=5):
    audio = record(seconds)
    segments, _ = _model.transcribe(audio, language="en")
    return " ".join(seg.text for seg in segments)

async def speak(text, voice="en-US-GuyNeural"):
    tts = edge_tts.Communicate(text, voice=voice)
    async for _ in tts.stream():
        pass
