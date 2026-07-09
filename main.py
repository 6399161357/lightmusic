import os
import asyncio
import time
import random
import psutil
import subprocess
import sys
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatMemberUpdated, VoiceChatStarted
from pyrogram.enums import ParseMode, ChatType, ChatMemberStatus
from pyrogram.errors import UserNotParticipant, ChatAdminRequired

from pymongo import MongoClient
import yt_dlp

# ==========================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================
load_dotenv()

# ----- TELEGRAM API -----
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
STRING_SESSION = os.getenv("STRING_SESSION")
MONGO_DB_URI = os.getenv("MONGO_DB_URI")

# ----- BOT SETTINGS -----
BOT_NAME = os.getenv("BOT_NAME", "MIDNIGHT MUSIC")
BOT_USERNAME = os.getenv("BOT_USERNAME", "your_bot_username")
OWNER_ID = int(os.getenv("OWNER_ID"))
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "@light_speedy")

# ----- LINKS -----
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/your_support")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/your_channel")
ADD_GROUP_LINK = os.getenv("ADD_GROUP_LINK", f"https://t.me/{BOT_USERNAME}?startgroup=true")

# ----- IMAGES -----
START_IMAGE_URL = os.getenv("START_IMAGE_URL", "https://files.catbox.moe/bq9t1k.png")
PING_IMAGE_URL = os.getenv("PING_IMAGE_URL", "")

# ----- PREMIUM EMOJIS -----
PREMIUM_EMOJI_DOWNLOAD = os.getenv("PREMIUM_EMOJI_DOWNLOAD")
PREMIUM_EMOJI_HELP = os.getenv("PREMIUM_EMOJI_HELP")
PREMIUM_EMOJI_SUPPORT = os.getenv("PREMIUM_EMOJI_SUPPORT")
PREMIUM_EMOJI_CHANNEL = os.getenv("PREMIUM_EMOJI_CHANNEL")
PREMIUM_EMOJI_OWNER = os.getenv("PREMIUM_EMOJI_OWNER")
PREMIUM_EMOJI_PLAY = os.getenv("PREMIUM_EMOJI_PLAY")
PREMIUM_EMOJI_NOW = os.getenv("PREMIUM_EMOJI_NOW")

# ----- YOUTUBE -----
COOKIE_FILE = os.getenv("COOKIE_FILE", "cookies.txt")
AUDIO_QUALITY = int(os.getenv("AUDIO_QUALITY", "320"))

# ==========================================
# INITIALIZE BOT
# ==========================================
bot = Client("midnight_music", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
assistant = Client("assistant", session_string=STRING_SESSION, api_id=API_ID, api_hash=API_HASH)

# Database
mongo = MongoClient(MONGO_DB_URI)
db = mongo["midnight_music"]
queue_db = db["queue"]
settings_db = db["settings"]

# Bot start time
BOT_START_TIME = datetime.now()

# ==========================================
# YOUTUBE OPTIMIZED
# ==========================================
ydl_opts = {
    'format': 'bestaudio/best',
    'cookiefile': COOKIE_FILE,
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'm4a',
        'preferredquality': str(AUDIO_QUALITY),
    }],
    'prefer_ffmpeg': True,
    'keepvideo': False,
    'noplaylist': True,
    'extractaudio': True,
    'audioformat': 'm4a',
    'throttledratelimit': 100000000,
    'socket_timeout': 10,
    'retries': 2,
    'fragment_retries': 2,
    'buffersize': 1024 * 1024,
    'http_chunk_size': 10485760,
    'geo_bypass': True,
    'geo_bypass_country': 'US',
}

# ==========================================
# VOICE CHAT FUNCTIONS
# ==========================================

async def join_vc(chat_id):
    """Join voice chat"""
    try:
        await assistant.join_chat(chat_id)
        await assistant.join_voice_chat(chat_id)
        return True
    except Exception as e:
        print(f"Error joining VC: {e}")
        return False

async def leave_vc(chat_id):
    """Leave voice chat"""
    try:
        await assistant.leave_voice_chat(chat_id)
        return True
    except Exception as e:
        print(f"Error leaving VC: {e}")
        return False

async def play_audio(chat_id, audio_url, title):
    """Play audio in voice chat"""
    try:
        # Download audio using yt-dlp
        audio_file = f"audio_{int(time.time())}.m4a"
        ydl_opts_download = {
            'format': 'bestaudio/best',
            'cookiefile': COOKIE_FILE,
            'outtmpl': audio_file,
            'quiet': True,
            'no_warnings': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '320',
            }],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
            ydl.download([audio_url])
        
        # Play audio in voice chat
        await assistant.play_voice_chat(chat_id, audio_file)
        return True
    except Exception as e:
        print(f"Error playing audio: {e}")
        return False

# ==========================================
# KEYBOARDS
# ==========================================
async def get_start_menu():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Add me to your group",
                    url=ADD_GROUP_LINK,
                )
            ],
            [
                InlineKeyboardButton(
                    "Help",
                    callback_data="help",
                )
            ],
            [
                InlineKeyboardButton(
                    "Support",
                    url=SUPPORT_LINK,
                ),
                InlineKeyboardButton(
                    "Channel",
                    url=CHANNEL_LINK,
                ),
                InlineKeyboardButton(
                    "Owner",
                    url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}",
                )
            ]
        ]
    )

async def get_ping_menu():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Channel",
                    url=CHANNEL_LINK,
                ),
                InlineKeyboardButton(
                    "Support",
                    url=SUPPORT_LINK,
                )
            ],
            [
                InlineKeyboardButton(
                    "Add Me to Your Group",
                    url=ADD_GROUP_LINK,
                )
            ]
        ]
    )

async def get_control_buttons():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Pause",
                    callback_data="pause",
                ),
                InlineKeyboardButton(
                    "Resume",
                    callback_data="resume",
                ),
                InlineKeyboardButton(
                    "Stop",
                    callback_data="stop",
                ),
                InlineKeyboardButton(
                    "Skip",
                    callback_data="skip",
                )
            ],
            [
                InlineKeyboardButton(
                    "Queue",
                    callback_data="queue",
                ),
                InlineKeyboardButton(
                    "Now Playing",
                    callback_data="now",
                )
            ]
        ]
    )

# ==========================================
# WELCOME MESSAGE
# ==========================================
@bot.on_chat_member_updated()
async def welcome_message(client: Client, event: ChatMemberUpdated):
    try:
        if event.new_chat_member and event.new_chat_member.status == ChatMemberStatus.MEMBER:
            if event.old_chat_member and event.old_chat_member.status == ChatMemberStatus.MEMBER:
                return
            
            user = event.new_chat_member.user
            welcome_text = (
                f"**🎉 WELCOME {user.mention}**\n\n"
                f"▸ Welcome to **{BOT_NAME}**!\n"
                f"▸ Enjoy high quality music without ads 🎵\n"
                f"▸ Use `/play` to start playing songs\n"
                f"▸ Owner: {OWNER_USERNAME}"
            )
            
            await bot.send_message(
                event.chat.id,
                welcome_text,
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        print(f"Welcome error: {e}")

# ==========================================
# START COMMAND
# ==========================================
@bot.on_message(filters.command("start"))
async def start_command(client, message):
    welcome_text = (
        f"**🎵 {BOT_NAME}**\n\n"
        "Hey {},\n"
        "This is **{}**! 🎵\n\n"
        "A music player bot with some awesome and useful features.\n\n"
        "🔗 Click on the **help** button for more info."
    ).format(message.from_user.mention, BOT_NAME)
    
    try:
        await message.reply_photo(
            photo=START_IMAGE_URL,
            caption=welcome_text,
            reply_markup=await get_start_menu(),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception:
        await message.reply_text(
            welcome_text,
            reply_markup=await get_start_menu(),
            parse_mode=ParseMode.MARKDOWN
        )

# ==========================================
# HELP COMMAND
# ==========================================
@bot.on_message(filters.command("help"))
async def help_command(client, message):
    help_text = (
        "**❓ Help & Commands**\n\n"
        "**🎮 Playback Controls:**\n"
        "▸ `/play` - Play a song (no ads, high quality)\n"
        "▸ `/pause` - Pause playback\n"
        "▸ `/resume` - Resume playback\n"
        "▸ `/stop` - Stop playback\n"
        "▸ `/skip` - Skip current song\n\n"
        "**📊 Information:**\n"
        "▸ `/now` - Current playing\n"
        "▸ `/queue` - Show queue\n"
        "▸ `/search` - Search YouTube\n\n"
        "**⚙️ Settings:**\n"
        "▸ `/volume` - Set volume (0-200)\n"
        "▸ `/ping` - Bot status\n\n"
        f"**👑 Owner:** {OWNER_USERNAME}"
    )
    
    await message.reply_text(
        help_text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        ),
        parse_mode=ParseMode.MARKDOWN
    )

# ==========================================
# PING COMMAND
# ==========================================
@bot.on_message(filters.command("ping"))
async def ping_command(client, message):
    uptime_delta = datetime.now() - BOT_START_TIME
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h: {minutes}m: {seconds}s"
    
    try:
        cpu_percent = psutil.cpu_percent()
        ram = psutil.virtual_memory()
        ram_used = ram.used / (1024**3)
        ram_total = ram.total / (1024**3)
    except:
        cpu_percent = 0
        ram_used = 0
        ram_total = 0
    
    ping_text = (
        "**PONG**\n\n"
        f"▸ LATENCY: `{(time.time() - BOT_START_TIME.timestamp()) * 1000:.2f}ms`\n"
        f"▸ UPTIME: `{uptime_str}`\n"
        f"▸ RAM: `{ram_used:.1f}GB / {ram_total:.1f}GB`\n"
        f"▸ CPU: `{cpu_percent:.1f}%`"
    )
    
    if PING_IMAGE_URL:
        try:
            await message.reply_photo(
                photo=PING_IMAGE_URL,
                caption=ping_text,
                reply_markup=await get_ping_menu(),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            await message.reply_text(
                ping_text,
                reply_markup=await get_ping_menu(),
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await message.reply_text(
            ping_text,
            reply_markup=await get_ping_menu(),
            parse_mode=ParseMode.MARKDOWN
        )

# ==========================================
# PLAY COMMAND
# ==========================================
@bot.on_message(filters.command("play"))
async def play_command(client, message):
    if not message.reply_to_message and len(message.command) < 2:
        await message.reply_text(
            "**⚠️ Error**\n\n▸ Please provide a song name or link!\n▸ Example: `/play Attention`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    query = " ".join(message.command[1:]) if len(message.command) > 1 else message.reply_to_message.text
    
    download_emoji = f"![tg://emoji?id={PREMIUM_EMOJI_DOWNLOAD}](tg://emoji?id={PREMIUM_EMOJI_DOWNLOAD})" if PREMIUM_EMOJI_DOWNLOAD else "🎧"
    
    downloading_msg = await message.reply_text(
        f"{download_emoji} **downloading...**\n\n▸ `{query}`",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Join VC
    try:
        await join_vc(message.chat.id)
    except Exception as e:
        await downloading_msg.edit_text(
            f"**❌ Error**\n\n▸ {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if not info or "entries" not in info or not info["entries"]:
                await downloading_msg.edit_text(
                    "**❌ Not Found**\n\n▸ No results found for your query!",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            song = info["entries"][0]
            title = song.get("title", "Unknown")
            url = song.get("webpage_url", "")
            thumbnail = song.get("thumbnail", "")
            duration = song.get("duration", 0)
            channel = song.get("channel", "Unknown")
            views = song.get("view_count", 0)
            
            mins, secs = divmod(duration, 60)
            duration_str = f"{mins}:{secs:02d}" if mins > 0 else f"0:{secs:02d}"
            
            await downloading_msg.delete()
            
            try:
                await message.reply_photo(
                    photo=thumbnail,
                    caption=(
                        f"**🎵 Now Playing**\n\n"
                        f"▸ **Title:** {title}\n"
                        f"▸ **Channel:** {channel}\n"
                        f"▸ **Duration:** {duration_str}\n"
                        f"▸ **Views:** {views:,}\n"
                        f"▸ **Requested by:** {message.from_user.mention}\n\n"
                        f"▸ **Status:** ▶️ Playing"
                    ),
                    reply_markup=await get_control_buttons()
                )
            except Exception:
                await message.reply_text(
                    f"**🎵 Now Playing**\n\n"
                    f"▸ **Title:** {title}\n"
                    f"▸ **Channel:** {channel}\n"
                    f"▸ **Duration:** {duration_str}\n"
                    f"▸ **Views:** {views:,}\n"
                    f"▸ **Requested by:** {message.from_user.mention}\n\n"
                    f"▸ **Status:** ▶️ Playing",
                    reply_markup=await get_control_buttons(),
                    parse_mode=ParseMode.MARKDOWN
                )
            
            queue_db.insert_one({
                "chat_id": message.chat.id,
                "title": title,
                "url": url,
                "thumbnail": thumbnail,
                "duration": duration,
                "duration_str": duration_str,
                "channel": channel,
                "user_id": message.from_user.id,
                "user_mention": message.from_user.mention,
                "added_at": datetime.now()
            })
            
            # Play audio
            await play_audio(message.chat.id, url, title)
            
        except Exception as e:
            await downloading_msg.edit_text(
                f"**❌ Error**\n\n▸ {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )

# ==========================================
# PAUSE COMMAND
# ==========================================
@bot.on_message(filters.command("pause"))
async def pause_command(client, message):
    try:
        await assistant.pause_voice_chat(message.chat.id)
        await message.reply_text(
            "**⏸️ Paused**\n\n▸ Playback has been paused\n▸ Use `/resume` to continue",
            reply_markup=await get_control_buttons(),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await message.reply_text(
            f"**❌ Error**\n\n▸ {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )

# ==========================================
# RESUME COMMAND
# ==========================================
@bot.on_message(filters.command("resume"))
async def resume_command(client, message):
    try:
        await assistant.resume_voice_chat(message.chat.id)
        await message.reply_text(
            "**▶️ Resumed**\n\n▸ Playback has been resumed\n▸ Enjoy your music! 🎵",
            reply_markup=await get_control_buttons(),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await message.reply_text(
            f"**❌ Error**\n\n▸ {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )

# ==========================================
# STOP COMMAND
# ==========================================
@bot.on_message(filters.command("stop"))
async def stop_command(client, message):
    try:
        await leave_vc(message.chat.id)
        queue_db.delete_many({"chat_id": message.chat.id})
        await message.reply_text(
            "**⏹️ Stopped**\n\n▸ Playback has been stopped\n▸ Left the voice chat\n▸ Queue cleared",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await message.reply_text(
            f"**❌ Error**\n\n▸ {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )

# ==========================================
# SKIP COMMAND
# ==========================================
@bot.on_message(filters.command("skip"))
async def skip_command(client, message):
    try:
        await assistant.stop_voice_chat(message.chat.id)
        await message.reply_text(
            "**⏭️ Skipped**\n\n▸ Current song has been skipped",
            reply_markup=await get_control_buttons(),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await message.reply_text(
            f"**❌ Error**\n\n▸ {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )

# ==========================================
# QUEUE COMMAND
# ==========================================
@bot.on_message(filters.command("queue"))
async def queue_command(client, message):
    queue_items = list(queue_db.find({"chat_id": message.chat.id}))
    if not queue_items:
        await message.reply_text(
            "**📋 Queue**\n\n▸ Queue is empty!\n▸ Add some songs with `/play`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    queue_text = "**📋 Current Queue**\n\n"
    for i, item in enumerate(queue_items[:10], 1):
        queue_text += f"▸ `{i}.` {item['title']}\n"
    
    if len(queue_items) > 10:
        queue_text += f"\n▸ And {len(queue_items) - 10} more..."
    
    await message.reply_text(
        queue_text,
        reply_markup=await get_control_buttons(),
        parse_mode=ParseMode.MARKDOWN
    )

# ==========================================
# NOW PLAYING COMMAND
# ==========================================
@bot.on_message(filters.command("now"))
async def now_command(client, message):
    try:
        queue_item = queue_db.find_one({"chat_id": message.chat.id})
        if queue_item:
            thumbnail = queue_item.get("thumbnail", "")
            if thumbnail:
                try:
                    await message.reply_photo(
                        photo=thumbnail,
                        caption=(
                            f"**🎵 Now Playing**\n\n"
                            f"▸ {queue_item['title']}\n"
                            f"▸ Status: ▶️ Playing"
                        ),
                        reply_markup=await get_control_buttons()
                    )
                except:
                    await message.reply_text(
                        f"**🎵 Now Playing**\n\n▸ {queue_item['title']}\n▸ Status: ▶️ Playing",
                        reply_markup=await get_control_buttons(),
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                await message.reply_text(
                    f"**🎵 Now Playing**\n\n▸ {queue_item['title']}\n▸ Status: ▶️ Playing",
                    reply_markup=await get_control_buttons(),
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await message.reply_text(
                "**❌ Error**\n\n▸ No track is currently playing!",
                parse_mode=ParseMode.MARKDOWN
            )
    except:
        await message.reply_text(
            "**❌ Error**\n\n▸ No track is currently playing!",
            parse_mode=ParseMode.MARKDOWN
        )

# ==========================================
# SEARCH COMMAND
# ==========================================
@bot.on_message(filters.command("search"))
async def search_command(client, message):
    if len(message.command) < 2:
        await message.reply_text(
            "**⚠️ Error**\n\n▸ Please provide a search query!\n▸ Example: `/search Believer`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    query = " ".join(message.command[1:])
    searching = await message.reply_text(
        f"**🔍 Searching for:** `{query}`",
        parse_mode=ParseMode.MARKDOWN
    )
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch5:{query}", download=False)
            if not info or "entries" not in info:
                await searching.edit_text(
                    "**❌ Not Found**\n\n▸ No results found!",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            results = "**🔍 Search Results**\n\n"
            for i, entry in enumerate(info["entries"][:5], 1):
                title = entry.get("title", "Unknown")
                duration = entry.get("duration", 0)
                mins, secs = divmod(duration, 60)
                results += f"▸ `{i}.` {title} ({mins}:{secs:02d})\n"
            
            results += f"\n▸ Use `/play {query}` to play the first result"
            
            await searching.edit_text(
                results,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await searching.edit_text(
                f"**❌ Error**\n\n▸ {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )

# ==========================================
# VOLUME COMMAND
# ==========================================
@bot.on_message(filters.command("volume"))
async def volume_command(client, message):
    if len(message.command) < 2:
        await message.reply_text(
            "**⚠️ Error**\n\n▸ Please provide a volume level (0-200)\n▸ Example: `/volume 80`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        volume = int(message.command[1])
        if volume < 0 or volume > 200:
            await message.reply_text(
                "**⚠️ Error**\n\n▸ Volume must be between 0 and 200!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await assistant.set_voice_chat_volume(message.chat.id, volume)
        await message.reply_text(
            f"**🔊 Volume Set**\n\n▸ Volume has been set to **{volume}%**",
            parse_mode=ParseMode.MARKDOWN
        )
    except ValueError:
        await message.reply_text(
            "**⚠️ Error**\n\n▸ Please provide a valid number!",
            parse_mode=ParseMode.MARKDOWN
        )

# ==========================================
# CALLBACK QUERIES
# ==========================================
@bot.on_callback_query()
async def handle_callback(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    
    if data == "help":
        await help_command(client, callback_query.message)
    elif data == "back":
        await start_command(client, callback_query.message)
    elif data == "pause":
        await pause_command(client, callback_query.message)
    elif data == "resume":
        await resume_command(client, callback_query.message)
    elif data == "stop":
        await stop_command(client, callback_query.message)
    elif data == "skip":
        await skip_command(client, callback_query.message)
    elif data == "queue":
        await queue_command(client, callback_query.message)
    elif data == "now":
        await now_command(client, callback_query.message)
    
    await callback_query.answer()

# ==========================================
# START BOT
# ==========================================
async def main():
    print(f"🎵 Starting {BOT_NAME}...")
    print("📱 Starting Assistant...")
    await assistant.start()
    print("🤖 Starting Bot...")
    await bot.start()
    print(f"✅ {BOT_NAME} is ready!")
    print(f"🚀 No Ads: {'Yes' if os.path.exists(COOKIE_FILE) else 'No'} | Quality: {AUDIO_QUALITY}kbps")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
