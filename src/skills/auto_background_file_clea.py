import os
import logging
import time
import datetime
from pathlib import Path
from typing import Optional

VOICE_DIR = '/path/to/voice/directory'
RETENTION_PERIOD = 30  # days

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def delete_old_audio_files(voice_dir: str, retention_period: int) -> None:
    """
    Deletes audio files older than the specified retention period from the voice directory.

    Args:
    voice_dir (str): The directory containing the audio files.
    retention_period (int): The number of days to retain the audio files.

    Returns:
    None
    """
    try:
        # Calculate the cutoff date for old files
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_period)

        # Iterate over all files in the voice directory
        for filename in os.listdir(voice_dir):
            file_path = os.path.join(voice_dir, filename)

            # Check if the file is an audio file and is older than the cutoff date
            if os.path.isfile(file_path) and filename.endswith(('.wav', '.mp3', '.ogg')):
                file_mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_mod_time < cutoff_date:
                    try:
                        # Attempt to delete the old audio file
                        os.remove(file_path)
                        logging.info(f'Deleted old audio file: {filename}')
                    except OSError as e:
                        # Log any file access errors that occur during deletion
                        logging.error(f'Error deleting file {filename}: {e}')
    except Exception as e:
        # Log any unexpected errors that occur during the file deletion process
        logging.error(f'Error deleting old audio files: {e}')

def periodic_file_cleanup(voice_dir: str, retention_period: int, interval: int = 60) -> None:
    """
    Periodically scans the voice directory for old audio files and deletes them.

    Args:
    voice_dir (str): The directory containing the audio files.
    retention_period (int): The number of days to retain the audio files.
    interval (int): The interval in seconds between each scan. Defaults to 60.

    Returns:
    None
    """
    while True:
        delete_old_audio_files(voice_dir, retention_period)
        time.sleep(interval)

if __name__ == '__main__':
    voice_dir = VOICE_DIR
    retention_period = RETENTION_PERIOD
    periodic_file_cleanup(voice_dir, retention_period)