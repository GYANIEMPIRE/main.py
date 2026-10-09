
import os
import json
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ChatJoinRequestHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

CONFIG_FILE = Path("config.json")

DEFAULT_CONFIG = {
    "welcome": "Hello! Thanks for requesting to join our channel.",
    "video": "",
    "voice": "",
    "link": "https://example.com/register",
}


def load_config():
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            return {**DEFAULT_CONFIG, **data}
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config):
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


config = load_config()


def is_admin(update: Update) -> bool:
    return bool(
        update.effective_user
        and update.effective_user.id == ADMIN_ID
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update):
        await update.effective_message.reply_text(
            "Admin Panel\n\n"
            "/setwelcome Your welcome message\n"
            "/setvideo VIDEO_FILE_ID\n"
            "/setvoice VOICE_FILE_ID\n"
            "/setlink https://your-registration-link.com\n"
            "/showconfig\n\n"
            "Send a video or voice note to get its file ID."
        )
    else:
        await update.effective_message.reply_text(
            "Welcome! This bot sends information to channel join requesters."
        )


async def join_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    request = update.chat_join_request
    if request is None:
        return

    # Optional channel restriction.
    if CHANNEL_ID:
        target = str(request.chat.id)
        username = (request.chat.username or "").lower()
        configured = CHANNEL_ID.strip().lower()

        if target != configured and username != configured.lstrip("@"):
            return

    user_chat_id = request.user_chat_id

    try:
        # Telegram requires this temporary chat ID for join requests.
        await context.bot.send_message(
            chat_id=user_chat_id,
            text=config["welcome"],
        )

        if config["video"]:
            await context.bot.send_video(
                chat_id=user_chat_id,
                video=config["video"],
            )

        if config["voice"]:
            await context.bot.send_voice(
                chat_id=user_chat_id,
                voice=config["voice"],
            )

        await context.bot.send_message(
            chat_id=user_chat_id,
            text=f"Registration link:\n{config['link']}",
        )

        logging.info("Welcome sequence sent for a join request.")

    except Exception:
        logging.exception("Could not send the join-request messages.")


async def setwelcome(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        return

    message = update.effective_message
    new_text = " ".join(context.args).strip()

    if not new_text:
        await message.reply_text(
            "Usage: /setwelcome Your new welcome message"
        )
        return

    config["welcome"] = new_text
    save_config(config)
    await message.reply_text("Welcome message updated.")


async def setvideo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        return

    message = update.effective_message
    file_id = " ".join(context.args).strip()

    if not file_id:
        await message.reply_text(
            "Usage: /setvideo VIDEO_FILE_ID"
        )
        return

    config["video"] = file_id
    save_config(config)
    await message.reply_text("Video updated.")


async def setvoice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        return

    message = update.effective_message
    file_id = " ".join(context.args).strip()

    if not file_id:
        await message.reply_text(
            "Usage: /setvoice VOICE_FILE_ID"
        )
        return

    config["voice"] = file_id
    save_config(config)
    await message.reply_text("Voice note updated.")


async def setlink(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        return

    message = update.effective_message
    link = " ".join(context.args).strip()

    if not link.startswith(("https://", "http://")):
        await message.reply_text(
            "Usage: /setlink https://your-registration-link.com"
        )
        return

    config["link"] = link
    save_config(config)
    await message.reply_text("Registration link updated.")


async def showconfig(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        return

    await update.effective_message.reply_text(
        f"Welcome: {config['welcome']}\n"
        f"Video set: {'Yes' if config['video'] else 'No'}\n"
        f"Voice set: {'Yes' if config['voice'] else 'No'}\n"
        f"Registration link: {config['link']}"
    )


async def media_file_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        return

    message = update.effective_message

    if message.video:
        file_id = message.video.file_id
        kind = "VIDEO"
    elif message.voice:
        file_id = message.voice.file_id
        kind = "VOICE"
    else:
        return

    await message.reply_text(
        f"{kind} FILE ID:\n{file_id}\n\n"
        f"Save it using /set{kind.lower()} FILE_ID"
    )


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Set the BOT_TOKEN environment variable.")
    if ADMIN_ID == 0:
        raise RuntimeError("Set your numeric ADMIN_ID.")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setwelcome", setwelcome))
    app.add_handler(CommandHandler("setvideo", setvideo))
    app.add_handler(CommandHandler("setvoice", setvoice))
    app.add_handler(CommandHandler("setlink", setlink))
    app.add_handler(CommandHandler("showconfig", showconfig))

    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & (filters.VIDEO | filters.VOICE),
            media_file_id,
        )
    )

    app.add_handler(ChatJoinRequestHandler(join_request))

    app.run_polling(
        allowed_updates=[
            "message",
            "chat_join_request",
        ]
    )


if __name__ == "__main__":
    main()
