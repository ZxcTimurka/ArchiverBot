import telebot
import os
import re
import logging
from datetime import datetime, timezone


BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN',
                      'TELEGRAM_BOT_TOKEN_HERE')
MEDIA_ARCHIVE_DIR = 'media_archive'
LOG_FILE_PREFIX = 'chatlog'
LOG_FILE_EXTENSION = '.log'

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

if not BOT_TOKEN or BOT_TOKEN == 'TELEGRAM_BOT_TOKEN_HERE':
    logger.error(
        "Пожалуйста, укажите ваш токен Telegram бота в переменной окружения TELEGRAM_BOT_TOKEN или замените плейсхолдер в коде!")
    exit()
bot = telebot.TeleBot(BOT_TOKEN)
logger.info("Бот инициализирован.")

try:
    os.makedirs(MEDIA_ARCHIVE_DIR, exist_ok=True)
    logger.info(f"Основная папка для медиа: {MEDIA_ARCHIVE_DIR}")
except OSError as e:
    logger.error(
        f"Не удалось создать папку для медиа '{MEDIA_ARCHIVE_DIR}': {e}", exc_info=True)
    exit()

def sanitize_filename(name):
    if not name:
        return "_unknown_"
    name = str(name)
    name = re.sub(r'[\\/*?:"<>|]+', '_', name)
    name = re.sub(r'[\s_]+', '_', name)
    name = name.strip('_. ')
    if name in (".", ".."):
        name = f"_reserved_{name}_"
    if not name:
        name = "_empty_"
    max_len = 100
    if len(name) > max_len:
        trunc_point = name.rfind('_', 0, max_len - 7)
        if trunc_point != -1:
            name = name[:trunc_point] + "_trunc"
        else:
            name = name[:max_len] + "_trunc"
    return name


def format_log_entry_human_readable(log_entry):
    lines = []
    lines.append("---")
    timestamp = log_entry['timestamp_unix']
    dt_object = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    if log_entry.get('edited'):
        lines.append(
            f"Статус: СООБЩЕНИЕ ИЗМЕНЕНО (ID: {log_entry['message_id']})")
        lines.append(
            f"Время изменения: {dt_object.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    else:
        lines.append(f"Время: {dt_object.strftime('%Y-%m-%d %H:%M:%S %Z')}")

        lines.append(f"ID Сообщения: {log_entry['message_id']}")

    chat_info = log_entry['chat']
    user_info = log_entry['user']
    chat_desc = f"Чат ID: {chat_info['id']} ({chat_info['type']})"
    if chat_info.get('title'):
        chat_desc = f"Чат: {chat_info['title']} (ID: {chat_info['id']})"
    elif chat_info.get('username'):
        chat_desc += f" @{chat_info['username']}"
    lines.append(chat_desc)

    user_desc = f"От: {user_info['first_name']}"
    if user_info.get('last_name'):
        user_desc += f" {user_info['last_name']}"
    if user_info.get('username'):
        user_desc += f" (@{user_info['username']})"
    user_desc += f" (ID: {user_info['id']})"
    if user_info.get('is_bot'):
        user_desc += " [БОТ]"
    lines.append(user_desc)

    lines.append(f"Тип: {log_entry['content_type']}")

    if log_entry.get('text'):
        lines.append(f"Текст: {log_entry['text']}")
    if log_entry.get('caption'):
        lines.append(f"Подпись: {log_entry['caption']}")

    if log_entry.get('contact_details'):
        contact = log_entry['contact_details']
        contact_name = contact['first_name']
        if contact.get('last_name'):
            contact_name += f" {contact['last_name']}"
        lines.append(f"Контакт: {contact_name}")
        lines.append(f"Номер телефона: {contact['phone_number']}")
        if contact.get('user_id'):
            lines.append(f"Telegram ID: {contact['user_id']}")

    if log_entry.get('poll_details'):
        poll = log_entry['poll_details']
        lines.append(f"Опрос: {poll['question']}")
        if poll.get('options'):
            lines.append("Варианты:")
            for i, option in enumerate(poll['options']):
                lines.append(f"  {i + 1}. {option}")

    if not log_entry.get('edited') and log_entry['content_type'] in CONTENT_TYPES_WITH_FILES:
        if log_entry.get('file_name'):
            lines.append(f"Имя файла: {log_entry['file_name']}")
        if log_entry.get('local_path'):
            lines.append(f"Сохранен как: {log_entry['local_path']}")
        elif log_entry.get('download_error'):
            lines.append(f"Ошибка скачивания: {log_entry['download_error']}")
        elif log_entry.get('file_id'):
            lines.append(f"File ID: {log_entry['file_id']}")

    if log_entry['content_type'] == 'sticker' and log_entry.get('sticker_emoji'):

        lines.append(f"Стикер эмодзи: {log_entry['sticker_emoji']}")
    if log_entry['content_type'] == 'location' and log_entry.get('location'):
        loc = log_entry['location']
        lines.append(f"Локация: lat={loc['latitude']}, lon={loc['longitude']}")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def get_log_filename(chat, user):
    base_name = ""
    if chat.type == 'private':
        user_part = user.first_name
        if user.last_name:
            user_part += f" {user.last_name}"
        if user.username:
            user_part += f" ({user.username})"
        base_name = f"private_{user_part}_{chat.id}"
    elif chat.title:
        base_name = chat.title
    else:
        base_name = f"{chat.type}_{chat.id}"
    sanitized_base = sanitize_filename(base_name)
    return f"{LOG_FILE_PREFIX}_{sanitized_base}{LOG_FILE_EXTENSION}"


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    chat = message.chat

    log_filename = get_log_filename(chat, user)

    chat_id_sanitized = sanitize_filename(str(chat.id))
    chat_media_dir = os.path.join(MEDIA_ARCHIVE_DIR, chat_id_sanitized)

    try:
        os.makedirs(chat_media_dir, exist_ok=True)
        logger.info(f"Папка для медиа чата {chat.id}: {chat_media_dir}")
    except OSError as e:
        logger.error(
            f"Не удалось создать папку для медиа чата '{chat_media_dir}': {e}", exc_info=True)

        bot.reply_to(
            message, f"Внимание: Не удалось создать папку для медиафайлов: {chat_media_dir}. Текстовые сообщения будут логироваться.")

    bot.reply_to(message,
                 f"Привет, {user.first_name}! Я буду архивировать все сообщения и скачивать медиафайлы из этого чата.\n"
                 f"Лог для этого чата будет вестись в файле:\n`{log_filename}`\n"
                 f"Медиафайлы будут сохраняться в папку:\n`{chat_media_dir}/`",
                 parse_mode="Markdown")
    logger.info(
        f"Пользователь {user.id} ({user.username or 'no_username'}) запустил бота в чате {chat.id} (Тип: {chat.type}, Название: {getattr(chat, 'title', 'N/A')}). Лог: {log_filename}")


CONTENT_TYPES_TO_ARCHIVE = ['text', 'audio', 'document', 'photo', 'sticker',
                            'video', 'video_note', 'voice', 'location', 'contact', 'venue', 'poll', 'dice']
CONTENT_TYPES_WITH_FILES = ['audio', 'document',
                            'photo', 'video', 'video_note', 'voice', 'sticker']


@bot.message_handler(content_types=CONTENT_TYPES_TO_ARCHIVE)
def archive_message(message):
    try:
        chat = message.chat
        user = message.from_user
        content_type = message.content_type

        log_filename = get_log_filename(chat, user)

        chat_id_sanitized = sanitize_filename(str(chat.id))
        chat_media_dir = os.path.join(MEDIA_ARCHIVE_DIR, chat_id_sanitized)

        try:
            os.makedirs(chat_media_dir, exist_ok=True)
        except OSError as e:
            logger.error(
                f"Не удалось создать папку для медиа чата '{chat_media_dir}' при обработке сообщения {message.message_id}: {e}", exc_info=True)

        log_entry = {
            'message_id': message.message_id,
            'timestamp_unix': message.date,
            'chat': {'id': chat.id, 'type': chat.type, 'title': getattr(chat, 'title', None), 'username': getattr(chat, 'username', None)},
            'user': {'id': user.id, 'is_bot': user.is_bot, 'first_name': user.first_name, 'last_name': getattr(user, 'last_name', None), 'username': getattr(user, 'username', None)},
            'text': message.text, 'caption': message.caption, 'content_type': content_type,
            'file_id': None, 'file_unique_id': None, 'file_name': None,
            'local_path': None, 'download_error': None,
            'location': None, 'sticker_emoji': None,
            'contact_details': None,
            'poll_details': None,
            'edited': False
        }

        file_to_download = None

        if content_type == 'photo':
            if message.photo:
                photo_size = message.photo[-1]
                log_entry['file_id'] = photo_size.file_id
                log_entry['file_unique_id'] = photo_size.file_unique_id
                file_to_download = photo_size
            else:
                logger.warning(
                    f"Получено сообщение 'photo' без данных фото (msg_id: {message.message_id}, chat_id: {chat.id})")
        elif content_type == 'document' and message.document:
            log_entry['file_id'] = message.document.file_id
            log_entry['file_unique_id'] = message.document.file_unique_id
            log_entry['file_name'] = message.document.file_name
            file_to_download = message.document
        elif content_type == 'video' and message.video:
            log_entry['file_id'] = message.video.file_id
            log_entry['file_unique_id'] = message.video.file_unique_id
            log_entry['file_name'] = getattr(message.video, 'file_name', None)
            file_to_download = message.video
        elif content_type == 'audio' and message.audio:
            log_entry['file_id'] = message.audio.file_id
            log_entry['file_unique_id'] = message.audio.file_unique_id
            log_entry['file_name'] = getattr(
                message.audio, 'file_name', None)
            if not log_entry['file_name']:
                log_entry['file_name'] = f"{getattr(message.audio, 'performer', 'UnknownArtist')}_{getattr(message.audio, 'title', 'UnknownTitle')}.mp3"
                log_entry['file_name'] = sanitize_filename(
                    log_entry['file_name'])
            file_to_download = message.audio
        elif content_type == 'voice' and message.voice:
            log_entry['file_id'] = message.voice.file_id
            log_entry['file_unique_id'] = message.voice.file_unique_id
            file_to_download = message.voice
        elif content_type == 'video_note' and message.video_note:
            log_entry['file_id'] = message.video_note.file_id
            log_entry['file_unique_id'] = message.video_note.file_unique_id
            file_to_download = message.video_note
        elif content_type == 'sticker' and message.sticker:
            log_entry['file_id'] = message.sticker.file_id
            log_entry['file_unique_id'] = message.sticker.file_unique_id
            log_entry['sticker_emoji'] = message.sticker.emoji
            file_to_download = message.sticker
        elif content_type == 'location' and message.location:
            log_entry['location'] = {
                'latitude': message.location.latitude, 'longitude': message.location.longitude}
        elif content_type == 'contact' and message.contact:
            contact = message.contact
            log_entry['contact_details'] = {
                'phone_number': contact.phone_number,
                'first_name': contact.first_name,
                'last_name': contact.last_name,
                'user_id': contact.user_id
            }
        elif content_type == 'poll' and message.poll:
            poll = message.poll
            log_entry['poll_details'] = {
                'id': poll.id,
                'question': poll.question,
                'options': [option.text for option in poll.options],
                'is_anonymous': poll.is_anonymous,
                'type': poll.type,
                'allows_multiple_answers': poll.allows_multiple_answers,
                'is_closed': poll.is_closed,
            }
        if file_to_download and content_type in CONTENT_TYPES_WITH_FILES:
            file_id = log_entry.get('file_id')
            file_unique_id = log_entry.get('file_unique_id')

            if file_id and file_unique_id:
                save_path = None
                try:
                    os.makedirs(chat_media_dir, exist_ok=True)

                    file_info = bot.get_file(file_id)
                    file_ext = ''

                    original_filename = log_entry.get('file_name')

                    if original_filename and '.' in original_filename:
                        _, file_ext = os.path.splitext(original_filename)
                    elif file_info.file_path and '.' in file_info.file_path:
                        _, file_ext = os.path.splitext(file_info.file_path)
                    else:
                        if content_type == 'sticker':
                            file_ext = '.webp'
                        elif content_type == 'photo':
                            file_ext = '.jpg'
                        elif content_type == 'voice':
                            file_ext = '.ogg'
                        elif content_type == 'video_note':
                            file_ext = '.mp4'
                        elif content_type == 'video':
                            file_ext = '.mp4'
                        elif content_type == 'audio':
                            file_ext = '.mp3'

                    local_filename = f"{file_unique_id}{file_ext}"
                    save_path = os.path.join(chat_media_dir, local_filename)

                    if original_filename and original_filename != local_filename:
                        log_entry['file_name'] = original_filename
                    elif not original_filename and file_ext:
                        log_entry['file_name'] = local_filename

                    logger.info(
                        f"Попытка скачивания файла: {file_id} (unique: {file_unique_id}) для чата {chat.id} в {save_path}")
                    downloaded_file = bot.download_file(file_info.file_path)
                    with open(save_path, 'wb') as new_file:
                        new_file.write(downloaded_file)

                    log_entry['local_path'] = save_path
                    logger.info(f"Файл успешно скачан и сохранен: {save_path}")

                except telebot.apihelper.ApiTelegramException as e:
                    error_msg = f"Telegram API error ({e.error_code}): {e.description}"
                    logger.warning(
                        f"Ошибка скачивания файла {file_id} для чата {chat.id}: {error_msg}")
                    log_entry['download_error'] = error_msg
                except OSError as e:
                    error_msg = f"OS error saving file: {e}"
                    logger.error(
                        f"Ошибка ОС при сохранении файла {file_id} в '{save_path}': {error_msg}", exc_info=True)
                    log_entry['download_error'] = error_msg
                except IOError as e:
                    error_msg = f"IO error saving file: {e}"
                    logger.error(
                        f"Ошибка ввода/вывода при сохранении файла {file_id} в '{save_path}': {error_msg}", exc_info=True)
                    log_entry['download_error'] = error_msg
                except Exception as e:
                    error_msg = f"Unexpected error during download/save: {e}"
                    logger.error(
                        f"Неожиданная ошибка при обработке файла {file_id} для чата {chat.id}: {error_msg}", exc_info=True)
                    log_entry['download_error'] = error_msg
            else:
                logger.warning(
                    f"Отсутствует file_id или file_unique_id для медиа в сообщении {message.message_id} (тип: {content_type}) в чате {chat.id}, скачивание невозможно.")
                log_entry['download_error'] = "Missing file_id or file_unique_id"

        try:
            log_string = format_log_entry_human_readable(log_entry)
            with open(log_filename, 'a', encoding='utf-8') as f:
                f.write(log_string)
            logger.info(
                f"Сообщение {log_entry['message_id']} ({content_type}) из чата {chat.id} пользователя {user.id} заархивировано в {log_filename}.")
        except Exception as e:
            logger.error(
                f"Ошибка записи в файл лога {log_filename}: {e}", exc_info=True)

    except Exception as e:
        chat_id_for_error = message.chat.id if message and hasattr(
            message, 'chat') else 'UNKNOWN_CHAT'
        message_id_for_error = message.message_id if message and hasattr(
            message, 'message_id') else 'UNKNOWN_MSG'
        logger.error(
            f"Критическая ошибка при обработке сообщения {message_id_for_error} в чате {chat_id_for_error}: {e}", exc_info=True)


@bot.edited_message_handler(content_types=CONTENT_TYPES_TO_ARCHIVE)
def archive_edited_message(message):
    try:
        chat = message.chat
        user = message.from_user
        content_type = message.content_type

        log_filename = get_log_filename(chat, user)

        edit_timestamp = getattr(message, 'edit_date', None)
        if not edit_timestamp:
            edit_timestamp = int(datetime.now(timezone.utc).timestamp())
            logger.warning(
                f"Отсутствует edit_date для измененного сообщения {message.message_id} в чате {chat.id}. Используется текущее время.")

        log_entry = {
            'message_id': message.message_id,
            'timestamp_unix': edit_timestamp,
            'chat': {'id': chat.id, 'type': chat.type, 'title': getattr(chat, 'title', None), 'username': getattr(chat, 'username', None)},
            'user': {'id': user.id, 'is_bot': user.is_bot, 'first_name': user.first_name, 'last_name': getattr(user, 'last_name', None), 'username': getattr(user, 'username', None)},
            'text': message.text,
            'caption': message.caption,
            'content_type': content_type,
            'edited': True,
            'file_id': None, 'file_unique_id': None, 'file_name': None,
            'local_path': None, 'download_error': None,
            'location': None, 'sticker_emoji': None,
            'contact_details': None,
            'poll_details': None,
        }

        if content_type == 'location' and message.location:
            log_entry['location'] = {
                'latitude': message.location.latitude, 'longitude': message.location.longitude}

        if content_type == 'sticker' and message.sticker:
            log_entry['sticker_emoji'] = message.sticker.emoji

        try:
            log_string = format_log_entry_human_readable(
                log_entry)
            with open(log_filename, 'a', encoding='utf-8') as f:
                f.write(log_string)
            logger.info(
                f"Измененное сообщение {log_entry['message_id']} ({content_type}) из чата {chat.id} пользователя {user.id} заархивировано в {log_filename}.")
        except Exception as e:
            logger.error(
                f"Ошибка записи измененного сообщения в файл лога {log_filename}: {e}", exc_info=True)

    except Exception as e:
        chat_id_for_error = message.chat.id if message and hasattr(
            message, 'chat') else 'UNKNOWN_CHAT'
        message_id_for_error = message.message_id if message and hasattr(
            message, 'message_id') else 'UNKNOWN_MSG'
        logger.error(
            f"Критическая ошибка при обработке ИЗМЕНЕННОГО сообщения {message_id_for_error} в чате {chat_id_for_error}: {e}", exc_info=True)


if __name__ == '__main__':
    logger.info("Запуск бота (polling)...")
    print("Бот запущен и готов к работе. Нажмите Ctrl+C для остановки.")
    try:
        bot.infinity_polling(logger_level=logging.WARNING,
                             timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        logger.info(
            "Получен сигнал остановки (KeyboardInterrupt). Завершение работы...")
        print("\nБот остановлен.")
    except Exception as e:
        logger.critical(
            f"Критическая ошибка в главном цикле polling бота: {e}", exc_info=True)
    finally:
        logger.info("Бот завершил работу.")
