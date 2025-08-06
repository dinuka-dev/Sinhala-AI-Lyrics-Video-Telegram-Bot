import api
import json
import gen
import os
import time
import re
import shutil
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
)

load_dotenv()

#CREATE A DIR IF NOT EXIST
if not os.path.exists("temp"):
    os.makedirs("temp")
if not os.path.exists("outputs"):
    os.makedirs("outputs")
if not os.path.exists("data"):
    os.makedirs("data")

def escape_markdown(text):
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
(
    SPOTIFY_URL, TIMES, IMAGE_SOURCE_CHOICE, IMAGE, FONT_SELECTION, SONG_TITLE_CHOICE, CUSTOM_SONG_TITLE
) = range(7)


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

USER_DATA = {} # Simple in-memory store for user inputs

def generate_video(spotify_url, start_time, end_time, raw_image_path, image_source_type, song_title=None, font=1):

    #GET TIMESTAMP IN SEC
    vid_id = int(time.time())

    #DOWNLOAD AUDIO
    try:
        download_link, title = api.get_download_link_temp(spotify_url)
    except:
        download_link, title = api.get_download_link_temp(spotify_url)

    if download_link == "":
        download_link, title = api.get_download_link_temp(spotify_url)

    audio_path = api.download_mp3(download_link, vid_id)
    if song_title is None:
        song_title = title

    #GET LYRICS AS STRING (moved up to be available for image generation if needed)
    lyrics_path = api.get_full_lyrics(song_title, vid_id)
    with open(lyrics_path, 'r', encoding='utf-8') as f_lyrics:
        lyrics_for_ghibli = json.load(f_lyrics)
    lyrics_as_str = gen.get_lyrics_as_str(start_time, end_time, lyrics_for_ghibli)

    # GENERATE GHIBLI IMAGE
    # raw_image_path is from USER_DATA (bot_temp path) or the "LYRICS_BASED" marker
    # image_source_type is passed as an argument from USER_DATA

    final_raw_image_path_for_json = None # Will be set based on image_source_type

    if image_source_type == "lyrics_based":
        final_raw_image_path_for_json = "lyrics_based"
        logger.info(f"Ghibli source: Lyrics based for song: {song_title}")
        ghibli_image_path = api.make_ghibli_image(
            image_path=None, vid_id=vid_id, lyrics_data=lyrics_as_str, source_type=image_source_type
        )
    elif image_source_type in ["raw_ghibli", "ghibli_char"]: # User provided a raw image
        if not (raw_image_path and os.path.exists(raw_image_path) and raw_image_path != "LYRICS_BASED"):
            raise ValueError(f"Raw image path '{raw_image_path}' is not valid for source type '{image_source_type}'")
        
        image_ext = raw_image_path.split(".")[-1]
        copied_raw_image_name = f"raw_{vid_id}.{image_ext}"
        destination_copied_raw_image = os.path.join('temp', copied_raw_image_name)
        shutil.copy(raw_image_path, destination_copied_raw_image)
        final_raw_image_path_for_json = destination_copied_raw_image

        logger.info(f"Ghibli source ({image_source_type}): Raw image {final_raw_image_path_for_json}")
        ghibli_image_path = api.make_ghibli_image(
            image_path=final_raw_image_path_for_json, vid_id=vid_id, source_type=image_source_type
        )
    else:
        raise ValueError(f"Invalid raw_image_path or image_source_type for Ghibli generation: {raw_image_path}")
    #CALCULATE DURATION
    duration = end_time - start_time

    #GENERATE RAW VIDEO     
    raw_video_path = gen.generate_raw_video(ghibli_image_path, duration, vid_id)
    cutted_audio_path = gen.cut_audio(audio_path, start_time, end_time, vid_id)
    with open(lyrics_path, 'r', encoding='utf-8') as json_file:
        lyrics = json.load(json_file)

    #GENERATE FINAL VIDEO
    text_extries = gen.time_adjust_for_lyrics(start_time, end_time, lyrics, adjusted_time=0.10)
    # Use a temporary path for the video with text
    temp_video_with_text_path = f"temp/text_video_initial_{vid_id}.mp4"
    gen.add_timed_text_to_video(raw_video_path, temp_video_with_text_path, text_extries, text_position="mid", the_font=font)
    final_video_path = gen.add_audio_to_video(temp_video_with_text_path, cutted_audio_path, vid_id)

    #SAVE DATA
    json_save_path = f"data/{vid_id}.json"
    # Ensure all paths in vid_data are absolute or consistently relative for later use
    # For simplicity, we are using paths relative to the script's execution directory.
    # Consider making them absolute if the script or data might move.


    vid_data = {
        "id": vid_id,
        "spotify_url": spotify_url,
        "song_title": song_title,
        "start_time": start_time,
        "end_time": end_time,
        "raw_image_path": final_raw_image_path_for_json, # Path to temp/raw_{vid_id}.ext or "lyrics_based"
        "ghibli_image_path": ghibli_image_path,
        "audio_path": audio_path,
        "cutted_audio_path": cutted_audio_path,
        "lyrics_path": lyrics_path,
        "image_source_type": image_source_type,
        "font": font,
        "final_video_path": final_video_path
    }
    with open(json_save_path, 'w', encoding='utf-8') as json_file:
        json.dump(vid_data, json_file, indent=4)

    # Clean up intermediate files from the initial generation
    if os.path.exists(raw_video_path): # This is the ghibli animated video without text/audio
        os.remove(raw_video_path)
    if os.path.exists(temp_video_with_text_path): # This is the video with text but no final audio
        os.remove(temp_video_with_text_path)
    # audio_path (full downloaded audio) and cutted_audio_path are kept as per vid_data
    # lyrics_path and ghibli_image_path are also kept

    return vid_data



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Hi! I'm your Music Video Generator Bot.\n"
        "Send /generate to start creating a video."
    )

async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the video generation conversation."""
    user_id = update.message.from_user.id
    USER_DATA[user_id] = {} # Clear previous data for this user
    await update.message.reply_text("Let's create a video! First, please send me the Spotify track URL.")
    return SPOTIFY_URL

async def spotify_url_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the Spotify URL and asks for start/end times."""
    user_id = update.message.from_user.id
    USER_DATA[user_id]['spotify_url'] = update.message.text
    await update.message.reply_text(
        "Great! Now, please send the start and end times for the video clip, separated by a space (e.g., '30 90' for 30s to 90s)."
    )
    return TIMES

async def times_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores times and asks for the image."""
    user_id = update.message.from_user.id
    try:
        start_time_str, end_time_str = update.message.text.split()
        start_time = int(start_time_str)
        end_time = int(end_time_str)
        if start_time >= end_time:
            await update.message.reply_text("Start time must be less than end time. Please try again.")
            return TIMES
        USER_DATA[user_id]['start_time'] = start_time
        USER_DATA[user_id]['end_time'] = end_time

        keyboard = [
            [InlineKeyboardButton("Lyrics Based BG Image", callback_data="img_src_lyrics")],
            [InlineKeyboardButton("Raw To Ghibli", callback_data="img_src_raw_ghibli")],
            [InlineKeyboardButton("Ghibili Using Raw Character", callback_data="img_src_ghibli_char")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Got the times! Now, how do you want to generate the background image?",
            reply_markup=reply_markup
        )
        return IMAGE_SOURCE_CHOICE
    except ValueError:
        await update.message.reply_text("Invalid format. Please send times like '30 90'. Try again.")
        return TIMES

async def image_source_option_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the image source type and proceeds accordingly."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    choice = query.data

    if choice == "img_src_lyrics":
        USER_DATA[user_id]['image_source_type'] = 'lyrics_based'
        USER_DATA[user_id]['raw_image_path'] = "LYRICS_BASED" # Special marker
        await query.edit_message_text(text="Okay, will generate a Ghibli image based on lyrics/song.")
        # Now ask for font
        reply_keyboard = [["1", "2", "3", "4", "5"]]
        await query.message.reply_text( # Send as a new message
            "Please select a font for the lyrics (1-5).",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return FONT_SELECTION
    elif choice in ["img_src_raw_ghibli", "img_src_ghibli_char"]:
        USER_DATA[user_id]['image_source_type'] = 'raw_ghibli' if choice == "img_src_raw_ghibli" else 'ghibli_char'
        await query.edit_message_text(text="Great! Please send the raw image you want to use.")
        return IMAGE # Proceed to get the image from the user
    return IMAGE_SOURCE_CHOICE # Should not happen

async def image_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the image, asks about song title, and proceeds to generation."""
    user_id = update.message.from_user.id
    photo_file = await update.message.photo[-1].get_file()
    
    # Ensure temp directory exists for bot downloads
    bot_temp_dir = "bot_temp"
    if not os.path.exists(bot_temp_dir):
        os.makedirs(bot_temp_dir)
        
    image_path = os.path.join(bot_temp_dir, f"{user_id}_{int(time.time())}.jpg")
    await photo_file.download_to_drive(image_path)
    # This raw_image_path is from bot_temp, will be copied to temp/raw_{vid_id} later if used
    USER_DATA[user_id]['raw_image_path'] = image_path

    reply_keyboard = [["1", "2", "3", "4", "5"]]
    await update.message.reply_text(
        "Image received! Now, please select a font for the lyrics (1-5).",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return FONT_SELECTION

async def font_selection_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the font selection and asks about song title."""
    user_id = update.message.from_user.id
    font_choice = update.message.text
    if font_choice.isdigit() and 1 <= int(font_choice) <= 5:
        USER_DATA[user_id]['font'] = int(font_choice)
    else:
        await update.message.reply_text("Invalid font choice. Please select a number between 1 and 5. Try again.", reply_markup=ReplyKeyboardRemove())
        # Resend font selection prompt
        reply_keyboard = [["1", "2", "3", "4", "5"]]
        await update.message.reply_text(
            "Please select a font for the lyrics (1-5).",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return FONT_SELECTION

    reply_keyboard = [["Use title from Spotify"], ["Enter custom title"]]
    await update.message.reply_text(
        "Font selected! Do you want to use the song title from Spotify or enter a custom one for lyrics search?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return SONG_TITLE_CHOICE

async def song_title_choice_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles song title choice and proceeds accordingly."""
    user_id = update.message.from_user.id
    choice = update.message.text

    if choice == "Use title from Spotify":
        USER_DATA[user_id]['song_title'] = None
        await update.message.reply_text("Okay, using title from Spotify. Generating video, please wait... This might take a few minutes.", reply_markup=ReplyKeyboardRemove())
        return await process_generation(update, context)
    elif choice == "Enter custom title":
        await update.message.reply_text("Please enter the custom song title for lyrics search.", reply_markup=ReplyKeyboardRemove())
        return CUSTOM_SONG_TITLE
    else:
        await update.message.reply_text("Invalid choice. Please use the buttons.", reply_markup=ReplyKeyboardRemove())
        return SONG_TITLE_CHOICE

async def custom_song_title_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores custom song title and proceeds to generation."""
    user_id = update.message.from_user.id
    USER_DATA[user_id]['song_title'] = update.message.text
    await update.message.reply_text("Custom title received. Generating video, please wait... This might take a few minutes.")
    return await process_generation(update, context)

async def process_generation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processes the video generation and sends the result."""
    user_id = update.message.from_user.id
    data = USER_DATA[user_id]

    try:
        vid_data = generate_video(
            spotify_url=data['spotify_url'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            raw_image_path=data['raw_image_path'], # This is bot_temp path or "LYRICS_BASED"
            image_source_type=data['image_source_type'],
            song_title=data.get('song_title'), # Use .get() for optional song_title
            font=data.get('font', 1) # Default to font 1 if not selected for some reason
        )
        final_video_path = vid_data["final_video_path"]
        vid_id = vid_data["id"]

        await update.message.reply_text("Video generated successfully!")
        await update.message.reply_video(video=open(final_video_path, 'rb'))

    except Exception as e:
        logger.error(f"Error generating video for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text(f"Sorry, an error occurred while generating the video: {e}")
        return ConversationHandler.END # Ensure conversation ends on error
    finally:
        # Clean up the downloaded image from bot_temp if it exists and is a path
        user_raw_image_path = data.get('raw_image_path')
        if user_raw_image_path and user_raw_image_path != "LYRICS_BASED" and os.path.exists(user_raw_image_path):
            os.remove(data['raw_image_path'])
        if user_id in USER_DATA:
            del USER_DATA[user_id] # Clean up user data

    return ConversationHandler.END



async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user_id = update.message.from_user.id
    if user_id in USER_DATA and 'raw_image_path' in USER_DATA[user_id] and os.path.exists(USER_DATA[user_id]['raw_image_path']):
        os.remove(USER_DATA[user_id]['raw_image_path']) # Clean up downloaded image if any
    if user_id in USER_DATA:
        del USER_DATA[user_id]

    await update.message.reply_text(
        "Operation cancelled.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def main() -> None:
    """Run the bot."""
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.error("Please set your TELEGRAM_BOT_TOKEN in the script.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("generate", generate_command),
        ],
        states={
            # Original generation states
            SPOTIFY_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, spotify_url_received)],
            TIMES: [MessageHandler(filters.TEXT & ~filters.COMMAND, times_received)],
            IMAGE_SOURCE_CHOICE: [CallbackQueryHandler(image_source_option_chosen, pattern="^img_src_")],
            IMAGE: [MessageHandler(filters.PHOTO, image_received)], # For when user uploads raw image
            FONT_SELECTION: [MessageHandler(filters.Regex("^[1-5]$"), font_selection_received)],
            SONG_TITLE_CHOICE: [MessageHandler(filters.Regex("^(Use title from Spotify|Enter custom title)$"), song_title_choice_received)],
            CUSTOM_SONG_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_song_title_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)

    logger.info("Bot started. Press Ctrl-C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
