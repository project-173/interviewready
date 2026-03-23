"""Audio utility functions for processing audio data."""

import io
import wave
from typing import Optional


def pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> bytes:
    """Convert raw PCM audio data to WAV format.

    Args:
        pcm_data: Raw PCM audio bytes
        sample_rate: Sample rate in Hz (default: 16000)
        channels: Number of channels (default: 1 for mono)
        sample_width: Sample width in bytes (default: 2 for 16-bit)

    Returns:
        WAV formatted audio bytes
    """
    # Create an in-memory WAV file
    wav_buffer = io.BytesIO()

    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)

    return wav_buffer.getvalue()


def validate_audio_format(audio_data: bytes) -> bool:
    """Validate if audio data is in a supported format.

    Args:
        audio_data: Audio data bytes

    Returns:
        True if valid WAV or other supported format
    """
    if len(audio_data) < 44:
        return False

    # Check for WAV header
    return audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE'