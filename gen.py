import cv2
import json
import os
import math
from sinhala_converter import convertor
import platform
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import textwrap

#CHECK THE OS
system = platform.system()
system = "Darwin"
if system == "Windows":
    from moviepy import ImageClip, CompositeVideoClip, VideoFileClip, AudioFileClip
elif system == "Darwin":
    from moviepy.editor import ImageClip, CompositeVideoClip, VideoFileClip, AudioFileClip

def generate_raw_video(image_path, duration, vid_id):
    save_path = f"temp/raw_{vid_id}.mp4"

    # --- Configuration ---
    frame_width = 720 # Video width
    frame_height = 900 # Video height
    fps = 60 # Frames per second

    # Wave motion configuration
    vertical_speed = 0.25  # Default: 0.25 Controls how fast the image moves vertically
    horizontal_oscillations = 2.0  # Default 2.0 Number of horizontal oscillations per vertical cycle
    wave_amplitude = 0.4  # Default: 0.4 Controls the width of the wave
    wave_height = 0.5  # Default: 0.5 Controls the height of the wave 

    # Check if input image exists
    if not os.path.exists(image_path):
        print(f"Error: Input image not found at '{image_path}'")
        exit()
    else:
        # Load the image
        print(f"Loading image: {image_path}")
        clip = ImageClip(image_path)
        img_w, img_h = clip.w, clip.h
        print(f"Original image dimensions: {img_w}x{img_h}")

    # Resize the image
    scale_factor = 0.8 # Default: 0.8
    new_w = int(img_w * scale_factor)
    new_h = int(img_h * scale_factor)

    print(f"Scaling image by {scale_factor:.2f}x -> new size: {new_w}x{new_h}")
    if system == "Windows":
        clip = clip.resized(width=new_w)
    else:
        clip = clip.resize(width=new_w) # Resize based on new width, maintains aspect ratio
    # Update dimensions after resizing
    current_img_w, current_img_h = clip.w, clip.h # Use clip.w, clip.h directly
    print(f"Image dimensions for animation: {current_img_w}x{current_img_h}")

    # Check if the scaled image is actually larger than the frame (important for radius calc)
    if current_img_w <= frame_width or current_img_h <= frame_height:
        print("Warning: Scaled image is not larger than the frame. Panning effect might be limited or absent.")

    def get_position_smooth(t):
        center_x = frame_width / 2
        center_y = frame_height / 2

        max_x_movement = (current_img_w - frame_width) / 2
        max_y_movement = (current_img_h - frame_height) / 2

        max_x_movement = max(0, max_x_movement)
        max_y_movement = max(0, max_y_movement)

        base_range = min(max_x_movement, max_y_movement)
        x_movement_range = base_range * wave_amplitude
        y_movement_range = base_range * wave_height

        x_movement_range = max(0, x_movement_range)
        y_movement_range = max(0, y_movement_range)

        angle = 2 * math.pi * vertical_speed * t

        vertical_position = -y_movement_range * math.cos(angle)

        horizontal_position = x_movement_range * math.sin(horizontal_oscillations * angle)

        image_center_x = center_x + horizontal_position
        image_center_y = center_y + vertical_position

        final_x = image_center_x - current_img_w / 2
        final_y = image_center_y - current_img_h / 2

        return (final_x, final_y)

    # Set the duration of the ImageClip
    if system == "Windows":
        clip = clip.with_duration(duration)
    else:
        clip = clip.set_duration(duration)

    # Apply the time-varying position
    if system == "Windows":
        moving_image = clip.with_position(get_position_smooth)
    else:                                     
        moving_image = clip.set_position(get_position_smooth)

    # Create a CompositeVideoClip to ensure the final video dimensions are correct
    print(f"Creating final video canvas with size: {frame_width}x{frame_height}")
    final_clip = CompositeVideoClip([moving_image], size=(frame_width, frame_height))
    if system == "Windows":
        final_clip = final_clip.with_duration(duration)
    else:
        final_clip = final_clip.set_duration(duration)

    # Write the video file to MP4
    print(f"Writing video to '{save_path}' (Duration: {duration}s, FPS: {fps})...")
    try:
        final_clip.write_videofile(
            save_path,
            fps=fps,
            codec='libx264',
            audio=False # No audio in this case
            )
        # Print success message
        print("\n--------------------")
        print(f"Raw video '{save_path}' created successfully!")
        print("--------------------")
        return save_path

    except Exception as e:
        print("\n--------------------")
        print(f"An error occurred during raw video writing: {e}")
        print("Please ensure FFMPEG is installed and accessible by MoviePy.")
        print("You might need to install it separately or ensure it's in your system's PATH.")
        print("--------------------")
 
def time_adjust_for_lyrics(start_time, end_time, lyrics, adjusted_time=0.30):
    for i, lyric in enumerate(lyrics):
        txt = lyric["lyric"]
        if txt == "":
            if i == len(lyrics) - 1:
                continue # LAST ITEM SO DON'T REMOVE IT EVEN IT'S EMPTY
            else:
                lyrics.remove(lyric)
                continue

    finalized_lyrics = []
    should_break = False
    transition_time = 0

    for i, lyric in enumerate(lyrics):
        l_start_str = lyric["time"]
        mins, secs = l_start_str.split(":")
        l_start = int(mins) * 60 + float(secs)
        if l_start < start_time:
            continue
        l_start = l_start - start_time
        l_start = l_start + adjusted_time
        
        next_lyric = lyrics[i + 1]
        next_l_start_str = next_lyric["time"]
        next_mins, next_secs = next_l_start_str.split(":")
        next_l_start = int(next_mins) * 60 + float(next_secs)
        
        if next_l_start >= end_time:
            l_end = end_time - start_time
            should_break = True
        else:
            l_end = (next_l_start - transition_time) - start_time

        finalized_lyrics.append({
            "start_time": l_start,
            "end_time": l_end,
            "text": lyric["lyric"]
        })

        if should_break:
            break

    with open('temp/adjusted_lyrics.json', 'w', encoding='utf-8') as json_file:
        json.dump(finalized_lyrics, json_file, ensure_ascii=False, indent=4)

    return finalized_lyrics

def get_lyrics_as_str(start_time, end_time, lyrics):
    for i, lyric in enumerate(lyrics):
        txt = lyric["lyric"]
        if txt == "":
            if i == len(lyrics) - 1:
                continue # LAST ITEM SO DON'T REMOVE IT EVEN IT'S EMPTY
            else:
                lyrics.remove(lyric)
                continue

    finalized_lyrics_str = ""
    should_break = False
    transition_time = 0

    for i, lyric in enumerate(lyrics):
        l_start_str = lyric["time"]
        mins, secs = l_start_str.split(":")
        l_start = int(mins) * 60 + float(secs)
        if l_start < start_time:
            continue
        l_start = l_start - start_time
        
        next_lyric = lyrics[i + 1]
        next_l_start_str = next_lyric["time"]
        next_mins, next_secs = next_l_start_str.split(":")
        next_l_start = int(next_mins) * 60 + float(next_secs)
        
        if next_l_start >= end_time:
            l_end = end_time - start_time
            should_break = True
        else:
            l_end = (next_l_start - transition_time) - start_time

        finalized_lyrics_str += f"{lyric['lyric']}\n"

        if should_break:
            break

    return finalized_lyrics_str

def add_timed_text_to_video(input_path, output_path, text_entries, the_font=1, text_position="mid"):
    # Video setup
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Text configuration
    sinhala_font = the_font
    if sinhala_font == 0:
        font_path = "/System/Library/Fonts/Supplemental/Sinhala MN.ttc" # MAC OS UNICODE FONT
    else:
        font_path = f"fonts/{the_font}.ttf"
    MAX_LINE_CHAR_LENGTH = 35 # Define the character limit for wrapping

    # Try to load a font
    try:
        font_size = 30
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        # Fallback to default font if font not found
        font = ImageFont.load_default()
        print("Warning: Sinhala font not found, using default font")
    
    line_spacing = 10
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        current_time = frame_count / fps

        # Convert OpenCV BGR to RGB for PIL
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)
        draw = ImageDraw.Draw(pil_img)

        for entry in text_entries:
            start = entry["start_time"]
            end = entry["end_time"]

            if start <= current_time <= end:
                text = entry["text"]

                # Original lines based on explicit newline characters
                initial_lines = text.split('\n')

                # Processed lines with wrapping for long lines
                processed_lines = []
                for single_line in initial_lines:
                    # Wrap the line if it's too long, textwrap handles empty strings correctly (returns [''])
                    wrapped_sub_lines = textwrap.wrap(single_line, width=MAX_LINE_CHAR_LENGTH, break_long_words=True, replace_whitespace=False)
                    processed_lines.extend(wrapped_sub_lines)
                
                # Calculate total text block height using the original method but with processed_lines
                # Note on font.getbbox(): It returns (left, top, right, bottom).
                # Original code uses bbox[3] (bottom) as height and bbox[2] (right) as width.
                # This assumes top and left are 0 or negligible.
                # More robust: height = bbox[3]-bbox[1], width = bbox[2]-bbox[0].
                # For this change, we'll stick to the original indexing to maintain existing rendering behavior.
                total_height = sum(
                    font.getbbox(line)[3] if line else 0 for line in processed_lines  # Use 0 height for empty lines
                ) + (len(processed_lines) - 1) * line_spacing if processed_lines else 0
                
                # Vertical starting position
                y_start = 0 # Default y_start
                if processed_lines: # Only calculate if there are lines to draw
                    if text_position == "mid":
                        y_start = (height - total_height) // 2
                    elif text_position == "bottom":
                        y_start = (height - total_height + 250) // 2 # Original offset
                
                # Draw each line
                for line in processed_lines:
                    if sinhala_font != 0:
                        line = convertor(line, 'fm')

                    text_render_width = font.getbbox(line)[2] # Using original method for width
                    current_line_render_height = font.getbbox(line)[3] # Using original method for height

                    x = (width - text_render_width) // 2  # Horizontal center

                    # Draw text with shadow for better visibility
                    draw.text((x+2, y_start+2), line, font=font, fill=(0, 0, 0))
                    draw.text((x, y_start), line, font=font, fill=(255, 255, 255))

                    y_start += current_line_render_height + line_spacing

        # Convert back to OpenCV format
        frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        out.write(frame)
        frame_count += 1

    cap.release()
    out.release()
    cv2.destroyAllWindows()

def cut_audio(input_path, start_time, end_time, vid_id):
    if system == "Windows":
        audio = AudioFileClip(input_path).subclipped(start_time, end_time)
    else:
        audio = AudioFileClip(input_path).subclip(start_time, end_time)
    
    output_path = f"temp/clip_{vid_id}.mp3"
    audio.write_audiofile(output_path)
    return output_path

def add_audio_to_video(input_video_path, input_audio_path, vid_id):
    save_path = f"outputs/final_{vid_id}.mp4"

    # Load the video and audio
    video = VideoFileClip(input_video_path)
    audio = AudioFileClip(input_audio_path)
    # Set the audio to the video
    if system == "Windows":
        final_video = video.with_audio(audio)
    else:
        final_video = video.set_audio(audio)

    # Export the final video
    final_video.write_videofile(save_path, codec="libx264", audio_codec="aac")
    return save_path