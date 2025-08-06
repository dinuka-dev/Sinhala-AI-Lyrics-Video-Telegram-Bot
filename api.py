import requests
import re
import json
from openai import OpenAI
import base64, pathlib
import os
from dotenv import load_dotenv

load_dotenv()

def find_between( s, first, last ):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ''

def get_download_link(spotify_url):
    url = "https://spotify-music-mp3-downloader-api.p.rapidapi.com/download"

    querystring = {"link": spotify_url}

    headers = {
        "x-rapidapi-key": os.getenv("RAPID_API_KEY"),
        "x-rapidapi-host": "spotify-music-mp3-downloader-api.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    json_res = response.json()
    print(json_res)
    download_link = json_res['data']['medias'][0]['url']
    title = json_res['data']['title']

    return download_link, title

def get_download_link_temp(spotify_url):

    params = {
        'url': 'https://spotmate.online/en',
        'token': os.getenv("SCRAPE_DO_API_KEY"),
        'render': 'true',
        'waitSelector': 'input#trackUrl',
        'returnJSON': 'true',
        'blockResources': 'false',
        'playWithBrowser': '[{"Action":"Fill","Selector":"#trackUrl","Value":"'+spotify_url+'"},{"Action":"Click","Selector":"#btnSubmit"},{"Action":"WaitSelector","WaitSelector":"#trackData","Timeout":10000},{"Action":"Click","Selector":"button.btn-success"},{"Action":"WaitSelector","WaitSelector":"a[data-url]","Timeout":5000},{"Action":"Wait","Timeout":5000}]',
    }

    response = requests.get('http://api.scrape.do/', params=params)
    json_res = response.json()

    track_name = ""
    download_link = ""

    networkRequests = json_res['networkRequests']
    for request in networkRequests:
        request_url = request.get('url', None)
        if not request_url:
            continue
        
        if request_url == "https://spotmate.online/convert":
            response_body = request['response_body']
            download_data = json.loads(response_body)
            download_link = download_data['url']
        
        if request_url == "https://spotmate.online/getTrackData":
            response_body = request['response_body']
            track_data = json.loads(response_body)
            track_name = track_data['name']

    return download_link, track_name

def download_mp3(url, vid_id):
    save_path = f"temp/audio_{vid_id}.mp3"

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise error for bad status

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        print(f"Downloaded successfully as '{save_path}'")
        return save_path
    except requests.exceptions.RequestException as e:
        print(f"Download failed: {e}")

def lyrics_to_json(lyrics_str):
    pattern = r"\[(\d{2}:\d{2}\.\d{2})\] ?(.*)"
    matches = re.findall(pattern, lyrics_str)

    result = []
    for time, lyric in matches:
        result.append({
            "time": time,
            "lyric": lyric.strip()
        })

    return json.dumps(result, ensure_ascii=False, indent=2)

def get_full_lyrics(keyword, vid_id):
    save_path = f"temp/lyrics_{vid_id}.json"

    headers = {
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Referer': 'https://lrclib.net',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'accept': 'application/json',
        'lrclib-client': 'LRCLIB Web Client (https://github.com/tranxuanthang/lrclib)',
        'x-user-agent': 'LRCLIB Web Client (https://github.com/tranxuanthang/lrclib)',
    }

    params = {
        'q': keyword,
    }

    response = requests.get('https://lrclib.net/api/search', params=params, headers=headers)
    json_res = response.json()
    syncedLyrics = json_res[0]['syncedLyrics']

    jsonLyrics = lyrics_to_json(syncedLyrics)
    with open(save_path, 'w', encoding='utf-8') as file:
        file.write(jsonLyrics)

    return save_path

def generate_prompt_for_image(lyrics_str):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  

    response = client.responses.create(
        model="gpt-4.1",
        input=[
            {
            "role": "system",
            "content": [
                {
                "type": "input_text",
                "text": "You are an prompt generation expert for image generation. "
                }
            ]
            },
            {
            "role": "user",
            "content": [
                {
                "type": "input_text",
                "text": f"I'm going to make a lyric video for a song. For this i need a background image and I'm going to generate an image using an AI model. So I'll give you the lyrics of this songs and you need to make the perfect image generation prompt for this background image. Make sure it's in Studio Ghibli art style and insert the prompt inside these tags <prompt></prompt>\n\nLyrics:\n{lyrics_str}"
                }
            ]
            }
        ],
        text={
            "format": {
            "type": "text"
            }
        },
        reasoning={},
        tools=[],
        temperature=1,
        max_output_tokens=2048,
        top_p=1,
        store=True
    )

    output_text = response.output_text
    prompt = find_between(output_text, "<prompt>", "</prompt>")

    return prompt.strip()

def make_ghibli_image(image_path, vid_id, source_type="raw_ghibli", lyrics_data=None):
    save_path = f"temp/ghibli_{vid_id}.png"

    if source_type == 'lyrics_based':
        prompt = generate_prompt_for_image(lyrics_data)
    elif source_type == 'raw_ghibli':
        stlye = "Fortnite" #Ghibli Studio, Caricature, Fortnite   More Styles: https://docs.codai.cloud/s/AP/p/convert-images-into-styles-eMJZxmQvO3
        prompt = f"Turn this image into {stlye} cartoon style"
    elif source_type == 'ghibli_char':
        prompt = "This person perform a song on a stage, Wide Shot, Studio Ghibli art"

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  

    if source_type == 'lyrics_based':
        response = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1536",
            quality="auto",
            output_format="png"
        )
        img_bytes = base64.b64decode(response.data[0].b64_json)
    else:
        with open(image_path, "rb") as image_file:
            edited = client.images.edit(
                model="gpt-image-1",
                image=image_file,
                prompt=prompt,
                size="1024x1536"
            )

        img_bytes = base64.b64decode(edited.data[0].b64_json)
    
    pathlib.Path(save_path).write_bytes(img_bytes)
    return save_path