import logging
import json
import os
import random
from telegram import Update, InputFile, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token and admin ID from environment variables
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_USER_ID = int(os.environ.get("TELEGRAM_ADMIN_ID")) if os.environ.get("TELEGRAM_ADMIN_ID") else None

if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
    exit()
if not ADMIN_USER_ID:
    logger.error("TELEGRAM_ADMIN_ID environment variable is not set!")
    exit()

PARTICIPANTS_FILE = "participants.json"
ASSIGNMENTS_FILE = "assignments.json"

# List of (username1, username2) pairs that should not be assigned to each other
# Make sure to include the '@' symbol for usernames.
EXCLUDED_PAIRS_USERNAMES = [
    ("@plzcult", "@DashaTiunova"),
    ("@Shosha_Espauzer", "@Vikessy"),
    ("@LevaMaster", "@BA_ANSHEE"),
    ("@plzcult", "@LevaMaster"),
    ("@plzcult", "@BA_ANSHEE")
]

# States for conversation handler
JOIN_NAME, WISHLIST_TEXT = range(2)
BROADCAST_TYPE, BROADCAST_CONTENT, BROADCAST_CONFIRM = range(2, 5)

def get_main_keyboard(chat_id: str) -> ReplyKeyboardMarkup:
    keyboard_buttons = []
    data = load_data()
    assignments_data = load_assignments()

    game_started = bool(assignments_data["assignments"])

    if chat_id not in data["participants"]:
        keyboard_buttons.append([KeyboardButton("🎅 Присоединиться к игре 🎄")])
    else:
        participant_info = data["participants"][chat_id]
        # Allow editing name and wishlist only if the game has not started
        if not game_started:
            keyboard_buttons.append([KeyboardButton("✏️ Изменить имя"), KeyboardButton("📝 Изменить письмо деду морозу 🎁")])
        
        if game_started and chat_id in assignments_data["assignments"]:
            keyboard_buttons.append([KeyboardButton("🎁 Мой Санта 🎅")])

    return ReplyKeyboardMarkup(keyboard_buttons, one_time_keyboard=False, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a video and asks for the name when the command /start is issued."""
    user = update.effective_user
    chat_id = str(update.effective_chat.id)
    data = load_data()
    assignments_data = load_assignments()
    game_started = bool(assignments_data["assignments"])

    if chat_id in data["participants"]:
        if game_started:
            await update.message.reply_text(
                "Привет! Игра уже началась, поэтому изменения имени и письма деду морозу больше невозможны.",
                reply_markup=get_main_keyboard(chat_id)
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                """Привет! Твоя текущая информация сохранена. Если хочешь изменить свое имя, просто нажми "✏️ Изменить имя". Если хочешь изменить письмо, нажми "📝 Изменить письмо деду морозу 🎁".""",
                reply_markup=get_main_keyboard(chat_id)
            )
            return ConversationHandler.END

    # Send the video
    try:
        with open("anton.mp4", 'rb') as video_file:
            await context.bot.send_video(chat_id=chat_id, video=InputFile(video_file))
    except FileNotFoundError:
        logger.error("anton.mp4 not found. Make sure the video file is in the same directory as main.py")
        await update.message.reply_text("Извини, я не могу найти видеофайл. Пожалуйста, сообщи администратору.")
        return ConversationHandler.END

    await update.message.reply_html(
        f"Привет, как тебя зовут? 🎅🎁🎄 (Это имя увидят другие участники)",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], one_time_keyboard=True, resize_keyboard=True)
    )
    return JOIN_NAME

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /help is issued."""
    chat_id = str(update.effective_chat.id)
    await update.message.reply_text("Используй кнопки ниже для взаимодействия.", reply_markup=get_main_keyboard(chat_id))

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation for joining the Secret Santa game."""
    chat_id = str(update.effective_chat.id)
    data = load_data()
    assignments_data = load_assignments()
    game_started = bool(assignments_data["assignments"])

    if chat_id in data["participants"]:
        if game_started:
            await update.message.reply_text("Игра уже началась, поэтому изменения имени и письма деду морозу больше невозможны.",
                                            reply_markup=get_main_keyboard(chat_id))
            return ConversationHandler.END
        else:
            await update.message.reply_text("""Ты уже зарегистрирован! Если хочешь изменить имя, "
                                        "используй кнопку "✏️ Изменить имя". Если хочешь изменить письмо деду морозу, используй кнопку "📝 Изменить письмо деду морозу 🎁".""",
                                        reply_markup=get_main_keyboard(chat_id))
            return ConversationHandler.END
    await update.message.reply_text("Привет! Как тебя зовут? (Это имя увидят другие участники)",
                                    reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], one_time_keyboard=True, resize_keyboard=True))
    return JOIN_NAME

async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the participant's name and saves it."""
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    name = update.message.text.strip()
    username = update.effective_user.username # Get username if available

    if not name:
        await update.message.reply_text("Имя не может быть пустым. Пожалуйста, введи свое имя.",
                                        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], one_time_keyboard=True, resize_keyboard=True))
        return JOIN_NAME

    data = load_data()
    
    participant_info = data["participants"].get(chat_id, {"user_id": user_id, "wishlist": None})
    participant_info["name"] = name
    participant_info["username"] = username
    
    data["participants"][chat_id] = participant_info
    save_data(data)

    await update.message.reply_text(
        f"Отлично, {name}! Твоя информация обновлена. "
        "Если ты еще не написал письмо деду морозу, самое время это сделать!",
        reply_markup=get_main_keyboard(chat_id)
    )
    return ConversationHandler.END

async def wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation for writing a wishlist."""
    chat_id = str(update.effective_chat.id)
    data = load_data()
    assignments_data = load_assignments()
    game_started = bool(assignments_data["assignments"])

    if chat_id not in data["participants"]:
        await update.message.reply_text("Сначала тебе нужно присоединиться к игре с помощью кнопки \"Присоединиться к игре\".",
                                        reply_markup=get_main_keyboard(chat_id))
        return ConversationHandler.END

    if game_started:
        await update.message.reply_text("Игра уже началась, поэтому изменения письма деду морозу больше невозможны.",
                                        reply_markup=get_main_keyboard(chat_id))
        return ConversationHandler.END

    await update.message.reply_text("Напиши свое письмо деду морозу для Тайного Санты. Будь креативным! (Это сообщение увидят)",
                                    reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], one_time_keyboard=True, resize_keyboard=True))
    return WISHLIST_TEXT

async def receive_wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the wishlist and saves it."""
    chat_id = str(update.effective_chat.id)
    wishlist_text = update.message.text.strip()

    if not wishlist_text:
        await update.message.reply_text("Письмо деду морозу не может быть пустым. Пожалуйста, напиши что-нибудь.",
                                        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], one_time_keyboard=True, resize_keyboard=True))
        return WISHLIST_TEXT

    data = load_data()
    if chat_id in data["participants"]:
        data["participants"][chat_id]["wishlist"] = wishlist_text
        save_data(data)
        await update.message.reply_text("Твое письмо деду морозу сохранено! Жди начала игры.",
                                        reply_markup=get_main_keyboard(chat_id))
    else:
        await update.message.reply_text("Кажется, ты не зарегистрирован. Используй кнопку \"Присоединиться к игре\", чтобы начать.",
                                        reply_markup=get_main_keyboard(chat_id))

    return ConversationHandler.END

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to start the Secret Santa game and assign participants."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("У тебя нет прав для выполнения этой команды.",
                                        reply_markup=get_main_keyboard(str(update.effective_chat.id)))
        return

    data = load_data()
    participants = list(data["participants"].values())

    if len(participants) < 2:
        await update.message.reply_text("Для начала игры необходимо минимум 2 участника.",
                                        reply_markup=get_main_keyboard(str(update.effective_chat.id)))
        return

    # Convert excluded usernames to user IDs
    excluded_pairs_user_ids = []
    for u1_username, u2_username in EXCLUDED_PAIRS_USERNAMES:
        u1_id = None
        u2_id = None
        for p in participants:
            # Telegram usernames can be None if not set by the user
            # We now primarily rely on 'name' for matching, as it's always provided during join.
            if p["name"] == u1_username.strip("@"):
                u1_id = p["user_id"]
            if p["name"] == u2_username.strip("@"):
                u2_id = p["user_id"]
        if u1_id and u2_id:
            excluded_pairs_user_ids.append((u1_id, u2_id))
            excluded_pairs_user_ids.append((u2_id, u1_id)) # Add reverse for easier checking
        else:
            # Log a warning if one of the excluded users is not found among participants
            logger.warning(
                f"Could not find one or both participants for excluded pair: ({u1_username}, {u2_username}). "
                f"Make sure they have joined and their name/username is correct."
            )

    # Check if all participants have a wishlist
    for p in participants:
        if not p["wishlist"]:
            await update.message.reply_text(
                f"Участник {p["name"]} еще не написал письмо деду морозу. Игра не может быть начата.",
                reply_markup=get_main_keyboard(str(update.effective_chat.id))
            )
            return

    # Shuffle participants to create assignments
    givers = participants[:]
    receivers = participants[:]
    random.shuffle(givers)
    random.shuffle(receivers)

    assignments = {}
    attempt_count = 0
    max_attempts = 100 # To prevent infinite loops in rare edge cases

    while True:
        current_assignments = {}
        valid_assignment = True
        temp_receivers = receivers[:]

        for i, giver in enumerate(givers):
            # Try to find a receiver that is not the giver themselves and not in excluded pairs
            possible_receivers = [
                r for r in temp_receivers 
                if r["user_id"] != giver["user_id"] and 
                (giver["user_id"], r["user_id"]) not in excluded_pairs_user_ids
            ]

            if not possible_receivers:
                valid_assignment = False
                break # Cannot make a valid assignment for this giver, restart the whole process

            receiver = random.choice(possible_receivers)
            current_assignments[giver["user_id"]] = receiver["user_id"]
            temp_receivers.remove(receiver)
        
        if valid_assignment and not temp_receivers: # All givers assigned and all receivers taken
            assignments = current_assignments
            break

        attempt_count += 1
        if attempt_count > max_attempts:
            await update.message.reply_text("Не удалось найти подходящие пары для Тайного Санты. Попробуй еще раз.",
                                            reply_markup=get_main_keyboard(str(update.effective_chat.id)))
            return
        random.shuffle(receivers) # Reshuffle receivers if assignment failed


    assignments_data = {"assignments": assignments}
    save_assignments(assignments_data)

    await update.message.reply_text("Игра Тайный Санта успешно начата! Участникам отправлены их подопечные.",
                                    reply_markup=get_main_keyboard(str(update.effective_chat.id)))

    # Notify each participant of their assigned person
    for giver_user_id, receiver_user_id in assignments.items():
        giver_chat_id = next(chat_id for chat_id, p_data in data["participants"].items() if p_data["user_id"] == giver_user_id)
        receiver_info = next(p_data for p_data in participants if p_data["user_id"] == receiver_user_id)
        
        try:
            receiver_link = f" (@{receiver_info["username"]})" if receiver_info["username"] else ""
            await context.application.bot.send_message(
                chat_id=giver_chat_id,
                text=f"Поздравляю! Твой подопечный в Тайном Санте - {receiver_info["name"]}{receiver_link}. "
                     f"Вот его письмо деду морозу:\n\n{receiver_info["wishlist"]}",
                reply_markup=get_main_keyboard(giver_chat_id)
            )
        except Exception as e:
            logger.error(f"Could not send message to {giver_user_id}: {e}")
            await update.message.reply_text(f"Не удалось отправить сообщение участнику {receiver_info["name"]}.",
                                            reply_markup=get_main_keyboard(str(update.effective_chat.id)))

async def my_santa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reveals the assigned person and their wishlist to the participant."""
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)

    assignments_data = load_assignments()
    participants_data = load_data()

    if user_id not in assignments_data["assignments"]:
        await update.message.reply_text("Игра еще не началась, или у тебя нет подопечного. Дождись начала игры.",
                                        reply_markup=get_main_keyboard(chat_id))
        return

    assigned_receiver_id = assignments_data["assignments"][user_id]
    
    receiver_info = None
    for c_id, p_data in participants_data["participants"].items():
        if p_data["user_id"] == assigned_receiver_id:
            receiver_info = p_data
            break

    if receiver_info:
        receiver_link = f" (@{receiver_info["username"]})" if receiver_info["username"] else ""
        await update.message.reply_text(
            f"Твой подопечный в Тайном Санте - {receiver_info["name"]}{receiver_link}. "
            f"Вот его письмо деду морозу:\n\n{receiver_info["wishlist"]}",
            reply_markup=get_main_keyboard(chat_id)
        )
    else:
        await update.message.reply_text("Не удалось найти информацию о твоем подопечном. Возможно, произошла ошибка.",
                                        reply_markup=get_main_keyboard(chat_id))

    
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    chat_id = str(update.effective_chat.id)
    await update.message.reply_text("Действие отменено.", reply_markup=get_main_keyboard(chat_id))
    return ConversationHandler.END

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin command to start a broadcast message to all participants."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("У тебя нет прав для выполнения этой команды.")
        return ConversationHandler.END

    keyboard = [
        [KeyboardButton("Текст"), KeyboardButton("Фото"), KeyboardButton("Видео")]
    ]
    await update.message.reply_text(
        "Что ты хочешь разослать всем участникам?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return BROADCAST_TYPE

async def receive_broadcast_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the type of broadcast message."""
    broadcast_type = update.message.text
    if broadcast_type not in ["Текст", "Фото", "Видео"]:
        await update.message.reply_text("Пожалуйста, выбери тип из предложенных кнопок.",
                                        reply_markup=ReplyKeyboardMarkup(
                                            [[KeyboardButton("Текст"), KeyboardButton("Фото"), KeyboardButton("Видео")]],
                                            one_time_keyboard=True, resize_keyboard=True))
        return BROADCAST_TYPE

    context.user_data["broadcast_type"] = broadcast_type
    await update.message.reply_text(
        f"Отправь {'текст' if broadcast_type == 'Текст' else 'фото' if broadcast_type == 'Фото' else 'видео'} для рассылки.",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], one_time_keyboard=True, resize_keyboard=True)
    )
    return BROADCAST_CONTENT

async def receive_broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the content for the broadcast message."""
    broadcast_type = context.user_data["broadcast_type"]
    content_to_send = None
    confirmation_message = ""

    if broadcast_type == "Текст":
        if not update.message.text:
            await update.message.reply_text("Текст не может быть пустым. Пожалуйста, отправь текст.")
            return BROADCAST_CONTENT
        content_to_send = update.message.text
        confirmation_message = f"Ты собираешься разослать следующий текст:\n\n{content_to_send}\n\nПодтверждаешь отправку?"

    elif broadcast_type == "Фото":
        if not update.message.photo:
            await update.message.reply_text("Пожалуйста, отправь фото.")
            return BROADCAST_CONTENT
        content_to_send = update.message.photo[-1].file_id # Get the largest photo
        confirmation_message = "Ты собираешься разослать это фото.\n\nПодтверждаешь отправку?"
        context.user_data["broadcast_file_id"] = content_to_send

    elif broadcast_type == "Видео":
        if not update.message.video:
            await update.message.reply_text("Пожалуйста, отправь видео.")
            return BROADCAST_CONTENT
        content_to_send = update.message.video.file_id
        confirmation_message = "Ты собираешься разослать это видео.\n\nПодтверждаешь отправку?"
        context.user_data["broadcast_file_id"] = content_to_send

    if content_to_send:
        context.user_data["broadcast_content"] = content_to_send
        keyboard = [[KeyboardButton("Да, отправить"), KeyboardButton("Нет, отмена")]]
        await update.message.reply_text(confirmation_message,
                                        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
        if broadcast_type == "Фото":
            await update.message.reply_photo(photo=content_to_send)
        elif broadcast_type == "Видео":
            await update.message.reply_video(video=content_to_send)
        return BROADCAST_CONFIRM
    return ConversationHandler.END

async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirms and sends the broadcast message to all participants."""
    if update.message.text == "Да, отправить":
        broadcast_type = context.user_data["broadcast_type"]
        content_to_send = context.user_data["broadcast_content"]
        
        data = load_data()
        participants = data.get("participants", {})

        sent_count = 0
        for chat_id, p_data in participants.items():
            try:
                if broadcast_type == "Текст":
                    await context.application.bot.send_message(chat_id=chat_id, text=content_to_send)
                elif broadcast_type == "Фото":
                    await context.application.bot.send_photo(chat_id=chat_id, photo=context.user_data["broadcast_file_id"])
                elif broadcast_type == "Видео":
                    await context.application.bot.send_video(chat_id=chat_id, video=context.user_data["broadcast_file_id"])
                sent_count += 1
            except Exception as e:
                logger.error(f"Could not send broadcast to {p_data.get("name", chat_id)} ({chat_id}): {e}")
        
        await update.message.reply_text(f"Рассылка завершена. Отправлено {sent_count} сообщений.",
                                        reply_markup=get_main_keyboard(str(update.effective_chat.id)))
    else:
        await update.message.reply_text("Рассылка отменена.",
                                        reply_markup=get_main_keyboard(str(update.effective_chat.id)))
    
    # Clear user data for broadcast
    context.user_data.pop("broadcast_type", None)
    context.user_data.pop("broadcast_content", None)
    context.user_data.pop("broadcast_file_id", None)
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    # You might want to send a message to yourself here to be notified of errors

def load_data():
    if os.path.exists(PARTICIPANTS_FILE):
        with open(PARTICIPANTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"participants": {}}

def save_data(data):
    with open(PARTICIPANTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_assignments():
    if os.path.exists(ASSIGNMENTS_FILE):
        with open(ASSIGNMENTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"assignments": {}}

def save_assignments(assignments_data):
    with open(ASSIGNMENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(assignments_data, f, ensure_ascii=False, indent=4)

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TOKEN).build()

    # On different commands - answer in Telegram
    application.add_handler(CommandHandler("help", help_command))

    # Conversation handler for /join and /start
    join_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("join", join),
            MessageHandler(filters.Regex("^🎅 Присоединиться к игре 🎄$|^✏️ Изменить имя$"), join)
        ],
        states={
            JOIN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(filters.Regex("^Отмена$"), cancel)],
    )
    application.add_handler(join_conv_handler)

    # Conversation handler for /wishlist
    wishlist_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("wishlist", wishlist),
            MessageHandler(filters.Regex("^📝 Написать письмо деду морозу 🎁$"), wishlist)
        ],
        states={
            WISHLIST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_wishlist)],
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(filters.Regex("^Отмена$"), cancel)],
    )
    application.add_handler(wishlist_conv_handler)

    application.add_handler(CommandHandler("start_game", start_game))
    application.add_handler(CommandHandler("my_santa", my_santa))
    application.add_handler(MessageHandler(filters.Regex("^🎁 Мой Санта 🎅$"), my_santa))

    # Conversation handler for broadcast functionality
    broadcast_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast)],
        states={
            BROADCAST_TYPE: [MessageHandler(filters.Regex("^(Текст|Фото|Видео)$"), receive_broadcast_type)],
            BROADCAST_CONTENT: [MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO & ~filters.COMMAND, receive_broadcast_content)],
            BROADCAST_CONFIRM: [MessageHandler(filters.Regex("^(Да, отправить|Нет, отмена)$"), confirm_broadcast)],
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(filters.Regex("^Отмена$"), cancel)],
    )
    application.add_handler(broadcast_conv_handler)

    # Log all errors
    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
