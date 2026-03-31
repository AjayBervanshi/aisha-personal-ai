with open("src/core/video_engine.py", "r") as f:
    code = f.read()

old_code = """    concat_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file_path,
        "-c", "copy", master_output
    ]

    try:
        subprocess.run(concat_cmd, capture_output=True, check=True)
        log.info(f"✅ Master video successfully produced: {master_output}")
        return master_output
    except subprocess.CalledProcessError as e:
        log.error(f"FFmpeg failed master stitch: {e.stderr.decode()}")
        return f"Error stitching master video: {e}" """

new_code = """    raw_output = os.path.join("temp_video", f"raw_{output_filename}")

    concat_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file_path,
        "-c", "copy", raw_output
    ]

    try:
        subprocess.run(concat_cmd, capture_output=True, check=True)
        log.info(f"🎥 Master video stitched: {raw_output}")

        # Post-Processing: Cinematic FX (Film Grain + Vignette)
        log.info("✨ Applying Cinematic FX (Film Grain, Vignette)...")
        master_output = os.path.join("temp_video", output_filename)
        fx_filter = "vignette=angle=3.14159:mode=forward,noise=alls=3:allf=t+u"

        fx_cmd = [
            "ffmpeg", "-y", "-i", raw_output, "-vf", fx_filter,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "copy", master_output
        ]
        subprocess.run(fx_cmd, capture_output=True, check=True)

        log.info(f"✅ Final Cinematic Video successfully produced: {master_output}")
        return master_output
    except subprocess.CalledProcessError as e:
        log.error(f"FFmpeg failed master stitch or FX: {e.stderr.decode()}")
        return f"Error processing master video: {e}" """

if old_code in code:
    code = code.replace(old_code, new_code)
    with open("src/core/video_engine.py", "w") as f:
        f.write(code)
    print("Successfully patched video_engine.py with Cinematic FX!")
else:
    print("Could not find the exact code block to patch in video_engine.py.")
