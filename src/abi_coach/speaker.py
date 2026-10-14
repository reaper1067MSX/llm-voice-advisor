"""Text-to-Speech (TTS) module for ABI Coach.

Uses edge-tts (default: female Mexican Spanish voice 'es-MX-DaliaNeural')
with miniaudio decoding and sounddevice playback.
Supports instant interruption when PTT is triggered again.
"""

import asyncio
import re
import threading
from typing import Optional
import edge_tts
import miniaudio
import numpy as np
import sounddevice as sd

from abi_coach.config import SpeakerConfig


class Speaker:
    def __init__(self, config: SpeakerConfig):
        self.config = config
        self._is_playing = False
        self._playback_lock = threading.Lock()

    def stop(self) -> None:
        """Interrupt and stop any currently playing speech."""
        with self._playback_lock:
            if self._is_playing:
                try:
                    sd.stop()
                except Exception:
                    pass
                self._is_playing = False

    def clean_text_for_speech(self, text: str) -> str:
        """Remove markdown syntax and special symbols so TTS speaks naturally."""
        # Remove bold/italic markers
        t = re.sub(r"[\*_#`~]", "", text)
        # Remove markdown links [text](url) -> text
        t = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", t)
        # Replace bullets with commas
        t = re.sub(r"^\s*[-•]\s*", ", ", t, flags=re.MULTILINE)
        # Clean extra whitespace
        t = re.sub(r"\s+", " ", t).strip()
        return t

    async def _generate_audio_edge(self, text: str) -> bytes:
        """Fetch MP3 bytes from edge-tts."""
        comm = edge_tts.Communicate(
            text=text,
            voice=self.config.voice,
            rate=self.config.rate,
            volume=self.config.volume,
        )
        audio_chunks = []
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
        return b"".join(audio_chunks)

    def _fallback_pyttsx3(self, text: str) -> None:
        """Fallback offline speech using Windows SAPI."""
        try:
            import pyttsx3

            engine = pyttsx3.init()
            # Try to pick a female Spanish voice if available
            voices = engine.getProperty("voices")
            for v in voices:
                v_name = v.name.lower()
                if "spanish" in v_name or "es-" in v.id.lower() or "sabina" in v_name or "helena" in v_name:
                    engine.setProperty("voice", v.id)
                    break
            engine.say(text)
            engine.runAndWait()
        except Exception:
            pass

    async def speak_async(self, text: str) -> None:
        """Convert text to speech and play aloud asynchronously."""
        clean = self.clean_text_for_speech(text)
        if not clean:
            return

        self.stop()

        try:
            mp3_bytes = await self._generate_audio_edge(clean)
            if not mp3_bytes:
                return

            decoded = miniaudio.decode(mp3_bytes)
            # Convert raw samples into numpy array
            audio_array = np.array(decoded.samples, dtype=np.int16)
            if decoded.nchannels > 1:
                audio_array = audio_array.reshape(-1, decoded.nchannels)

            # Calculate duration in seconds
            total_frames = len(audio_array) if decoded.nchannels == 1 else len(audio_array)
            duration_sec = total_frames / decoded.sample_rate

            with self._playback_lock:
                self._is_playing = True
                sd.play(audio_array, samplerate=decoded.sample_rate)

            # Wait for audio to finish playing or until interrupted
            import time
            end_time = time.perf_counter() + duration_sec
            while time.perf_counter() < end_time and self._is_playing:
                await asyncio.sleep(0.05)

        except Exception as e:
            # Fallback to offline SAPI
            self._fallback_pyttsx3(clean)
        finally:
            self._is_playing = False

    def speak(self, text: str) -> None:
        """Synchronous wrapper for speak_async."""
        asyncio.run(self.speak_async(text))
