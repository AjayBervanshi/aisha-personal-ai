import logging
import os
import soundfile as sf
import numpy as np
from pydub import AudioSegment
from pydub.silence import split_on_silence
from pydub.playback import play

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def noise_reduction(audio_file_path):
    """
    Reduces noise from an audio file.

    Args:
        audio_file_path (str): Path to the audio file.

    Returns:
        str: Path to the noise-reduced audio file.
    """
    try:
        sound = AudioSegment.from_file(audio_file_path)
        sound_with_noise_reduced = sound.apply_gain(-20.0 - sound.dBFS)
        noise_reduced_file_path = os.path.splitext(audio_file_path)[0] + "_noise_reduced.wav"
        sound_with_noise_reduced.export(noise_reduced_file_path, format="wav")
        return noise_reduced_file_path
    except Exception as e:
        logger.error(f"Error reducing noise: {e}")
        return None

def silence_trimming(audio_file_path):
    """
    Trims silence from an audio file.

    Args:
        audio_file_path (str): Path to the audio file.

    Returns:
        str: Path to the silence-trimmed audio file.
    """
    try:
        sound = AudioSegment.from_file(audio_file_path)
        chunks = split_on_silence(sound, min_silence_len=500, silence_thresh=-16)
        trimmed_file_path = os.path.splitext(audio_file_path)[0] + "_trimmed.wav"
        combined = chunks[0]
        for chunk in chunks[1:]:
            combined += chunk
        combined.export(trimmed_file_path, format="wav")
        return trimmed_file_path
    except Exception as e:
        logger.error(f"Error trimming silence: {e}")
        return None

def volume_normalization(audio_file_path):
    """
    Normalizes the volume of an audio file.

    Args:
        audio_file_path (str): Path to the audio file.

    Returns:
        str: Path to the volume-normalized audio file.
    """
    try:
        sound = AudioSegment.from_file(audio_file_path)
        sound_with_volume_normalized = sound.apply_gain(-20.0 - sound.dBFS)
        normalized_file_path = os.path.splitext(audio_file_path)[0] + "_normalized.wav"
        sound_with_volume_normalized.export(normalized_file_path, format="wav")
        return normalized_file_path
    except Exception as e:
        logger.error(f"Error normalizing volume: {e}")
        return None

def process_audio(audio_file_path):
    """
    Preprocesses an audio file by reducing noise, trimming silence, and normalizing volume.

    Args:
        audio_file_path (str): Path to the audio file.

    Returns:
        str: Path to the preprocessed audio file.
    """
    try:
        noise_reduced_file_path = noise_reduction(audio_file_path)
        trimmed_file_path = silence_trimming(noise_reduced_file_path)
        normalized_file_path = volume_normalization(trimmed_file_path)
        return normalized_file_path
    except Exception as e:
        logger.error(f"Error preprocessing audio: {e}")
        return None

if __name__ == "__main__":
    audio_file_path = "test_audio.wav"
    preprocessed_audio_file_path = process_audio(audio_file_path)
    logger.info(f"Preprocessed audio file path: {preprocessed_audio_file_path}")