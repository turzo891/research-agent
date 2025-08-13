import sounddevice as sd
import numpy as np
import asyncio, edge_tts

_sr = 16000
_model = None

def transcribe(seconds=5):
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("base", compute_type="int8")
    audio = record(seconds)
    segments, _ = _model.transcribe(audio, language="en")
    return " ".join(seg.text for seg in segments)

def record(seconds=5, samplerate=_sr):
    audio = sd.rec(int(seconds*samplerate), samplerate=samplerate, channels=1, dtype='float32')
    sd.wait()
    return audio.flatten()

async def speak(text, voice="en-US-GuyNeural"):
    tts = edge_tts.Communicate(text, voice=voice)
    async for _ in tts.stream():
        pass

# import asyncio
# from agent.voice import speak

# async def main():
#     await speak("System online. JARVIS at your service.")

# asyncio.run(main())
