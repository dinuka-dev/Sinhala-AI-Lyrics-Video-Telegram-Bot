import api
import json
import gen
import os
import time
import shutil

#CREATE DIRs IF NOT EXIST
if not os.path.exists("temp"):
    os.makedirs("temp")
if not os.path.exists("outputs"):
    os.makedirs("outputs")
if not os.path.exists("data"):
    os.makedirs("data")

def generate_video(spotify_url, start_time, end_time, raw_image_path, song_title=None, font=1):
    #GET TIMESTAMP IN SEC
    vid_id = int(time.time())

    #COPY RAW IMAGE
    image_ext = raw_image_path.split(".")[-1]
    new_image_name = f"raw_{vid_id}.{image_ext}"
    destination = os.path.join('temp', new_image_name)
    shutil.copy(raw_image_path, destination)
    raw_image_path = f"temp/{new_image_name}"

    #DOWNLOAD AUDIO
    download_link, title = api.get_download_link(spotify_url)
    audio_path = api.download_mp3(download_link, vid_id)
    if song_title is None:
        song_title = title

    #GET LYRICS
    lyrics_path = api.get_full_lyrics(song_title, vid_id)

    #GENERATE GHIBLI IMAGE
    ghibli_image_path = api.make_ghibli_image(raw_image_path, vid_id)

    #CALCULATE DURATION
    duration = end_time - start_time

    #GENERATE RAW VIDEO     
    raw_video_path = gen.generate_raw_video(ghibli_image_path, duration, vid_id)
    cutted_audio_path = gen.cut_audio(audio_path, start_time, end_time, vid_id)
    with open(lyrics_path, 'r', encoding='utf-8') as json_file:
        lyrics = json.load(json_file)

    #GENERATE FINAL VIDEO
    text_extries = gen.time_adjust_for_lyrics(start_time, end_time, lyrics, adjusted_time=0.10)
    gen.add_timed_text_to_video(raw_video_path, "outputs.mp4", text_extries, text_position="mid", the_font=font)
    final_video_path = gen.add_audio_to_video("outputs.mp4", cutted_audio_path, vid_id)

    #SAVE DATA
    json_save_path = f"data/{vid_id}.json"
    vid_data = {
        "id": vid_id,
        "spotify_url": spotify_url,
        "song_title": song_title,
        "start_time": start_time,
        "end_time": end_time,
        "raw_image_path": raw_image_path,
        "ghibli_image_path": ghibli_image_path,
        "audio_path": audio_path,
        "cutted_audio_path": cutted_audio_path,
        "lyrics_path": lyrics_path,
        "font": font,
        "final_video_path": final_video_path
    }
    with open(json_save_path, 'w', encoding='utf-8') as json_file:
        json.dump(vid_data, json_file, indent=4)

    return vid_data