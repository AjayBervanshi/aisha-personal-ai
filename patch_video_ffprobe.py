with open("src/core/video_engine.py", "r") as f:
    code = f.read()

old_ffprobe = """def _get_audio_duration(audio_path: str) -> float:
    \"\"\"Uses ffprobe to get the exact duration of an audio file in seconds.\"\"\"
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", audio_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        log.error(f"Failed to get audio duration for {audio_path}: {e}")
        return 5.0 # Fallback 5 seconds"""

new_ffprobe = """def _get_audio_duration(audio_path: str) -> float:
    \"\"\"Uses ffprobe to get the exact duration of an audio file in seconds.
    Falls back to a safe calculation if ffprobe is missing or fails.\"\"\"

    if not os.path.exists(audio_path):
        log.error(f"File not found: {audio_path}")
        return 0.0

    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", audio_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        log.error(f"Failed to get audio duration via ffprobe: {e}")
        # Fallback 1: Try mutagen if installed
        try:
            from mutagen.mp3 import MP3
            audio = MP3(audio_path)
            return float(audio.info.length)
        except Exception as mut_e:
            log.warning(f"Mutagen fallback failed: {mut_e}")

        # Fallback 2: Estimate based on file size (assuming standard 192k mp3)
        # 192 kbps = 24 KB/s. So seconds = size_in_kb / 24
        size_kb = os.path.getsize(audio_path) / 1024
        est_duration = size_kb / 24.0
        if est_duration > 0.5:
            return float(est_duration)

        return 5.0 # Absolute worst-case fallback"""

if old_ffprobe in code:
    code = code.replace(old_ffprobe, new_ffprobe)
    with open("src/core/video_engine.py", "w") as f:
        f.write(code)
    print("Successfully patched video_engine.py ffprobe fallback!")
else:
    print("Could not find the exact code block to patch in video_engine.py.")
