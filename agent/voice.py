import os, asyncio
from pathlib import Path
import edge_tts
from playsound import playsound

# --- Optional STT (lazy-loaded so TTS tests don't download models) ---
import sounddevice as sd
import numpy as np

_sr = 16000
_whisper = None

def record(seconds=5, samplerate=_sr):
    audio = sd.rec(int(seconds*samplerate), samplerate=samplerate, channels=1, dtype='float32')
    sd.wait()
    return audio.flatten()

def transcribe(seconds=5):
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        _whisper = WhisperModel("base", compute_type="int8")  # loads only when first used
    audio = record(seconds)
    segments, _ = _whisper.transcribe(audio, language="en")
    return " ".join(seg.text for seg in segments)

# --- TTS that actually plays audio ---
_CACHE = Path("data/cache")
_CACHE.mkdir(parents=True, exist_ok=True)

async def speak(text: str, voice: str = "en-US-GuyNeural", outfile: str = None):
    """
    Generate speech with Edge TTS, save to an mp3, and play it.
    """
    if not outfile:
        outfile = _CACHE / "tts_output.mp3"
    else:
        outfile = Path(outfile)
        outfile.parent.mkdir(parents=True, exist_ok=True)

    tts = edge_tts.Communicate(text, voice=voice)
    await tts.save(str(outfile))          # write mp3
    playsound(str(outfile))               # play it blocking

# Offline alternative:
from piper import PiperVoice
_voice = None

def speak_offline(text, model_path="en_US-amy-low.onnx", out="data/cache/tts_piper.wav"):
    global _voice
    if _voice is None:
        _voice = PiperVoice.load(model_path)   # download model once and keep locally
    audio = _voice.synthesize(text)            # returns 16kHz PCM
    from scipy.io.wavfile import write
    os.makedirs(os.path.dirname(out), exist_ok=True)
    write(out, 16000, audio)
    from playsound import playsound
    playsound(out)
# import sounddevice as sd
# import numpy as np
# from faster_whisper import WhisperModel
# import asyncio, edge_tts

# _sr = 16000
# _model = WhisperModel("base", compute_type="int8")

# def record(seconds=5, samplerate=_sr):
#     audio = sd.rec(int(seconds*samplerate), samplerate=samplerate, channels=1, dtype='float32')
#     sd.wait()
#     return audio.flatten()

# def transcribe(seconds=5):
#     audio = record(seconds)
#     segments, _ = _model.transcribe(audio, language="en")
#     return " ".join(seg.text for seg in segments)

# async def speak(text, voice="en-US-GuyNeural"):
#     tts = edge_tts.Communicate(text, voice=voice)
#     async for _ in tts.stream():
#         pass
