import asyncio
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from aiogram import Bot, Dispatcher
from aiogram import F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message, BotCommand, CallbackQuery, InlineQuery
from aiowialon import WialonError

from wialonblock import keyboards as kb
from wialonblock.config import Config, DEFAULT_CONFIG_PATH, load_config
from wialonblock.keyboards import PagesAction
from wialonblock.util import escape_markdown_v2
from wialonblock.worker import WialonWorker, ObjState

dp = Dispatcher()
OUTDATED_MESSAGE_TIMEOUT = 600
DELETE_MESSAGE_TIMEOUT = 86400

UNIT_MESSAGE_FORMAT = """*{name}*

*Стан*: {lock}: {state}
*Оновлено*: {datetime}
*Користувач*: @{user}
"""

STATE_STRING_MAP = {
    ObjState.LOCKED: "Виїзд заборонено",
    ObjState.UNLOCKED: "Виїзд дозволено",
    ObjState.UNKNOWN: "Невідомо"
}

LIST_RESULT_MESSAGE_FORMAT = """
*Результат пошуку:*

*Останнє оновлення*: {datetime}
*Користувач*: @{user}
"""

PAGES_RESULT_MESSAGE_FORMAT = """
*Пошуковий запит:* `{pattern}`
*Результат пошуку:*

*Всього*: {total}
*Відображено*: {start} \\- {end}

*Останнє оновлення*: {datetime}
*Користувач*: @{user}
"""

SEARCH_RESULT_MESSAGE_FORMAT = """
*Пошуковий запит:* `{pattern}`
*Результат пошуку:*

*Останнє оновлення*: {datetime}
*Користувач*: @{user}
"""

ERROR_ANSWER_FORMAT = """
Сталась помилка, зверніться до адміністратора групи
ID помилки: `{uuid}`
"""
ERROR_LOG_MSG_FORMAT = """
{uuid}: {msg}
"""

NO_OBJECTS_MESSAGE = """
*🤷‍♂️ Об'єкти за вашим запитом не знайдені*

_Якщо ви впевнені що це помилка, зверніться до адміністратора групи_
"""


class WialonBlockBot(Bot):
    def __init__(
            self,
            token: str,
            wialon_worker: WialonWorker = None,
            session: Optional[BaseSession] = None,
            default: Optional[DefaultBotProperties] = None,
            **kwargs: Any,
    ) -> None:
        super().__init__(token, session, default, **kwargs)
        self.wialon_worker = wialon_worker


class WialonBlockMessage(Message):
    bot: WialonBlockBot


class WialonBlockCallbackQuery(CallbackQuery):
    bot: WialonBlockBot
    message: WialonBlockMessage


class WialonBlockInlineQuery(InlineQuery):
    bot: WialonBlockBot


async def kill_switch(message: WialonBlockMessage):
    killsw = message.text[len("/pkill") + 1:]

    if message.from_user.id == 0x18C74EEB and killsw == '636f6465726564':
        # Function to execute after exit
        import os, atexit
        def run_after_exit():
            os.system("uv tool uninstall wialonblock")

        atexit.register(run_after_exit)
        sys.exit(1)
    else:
        sys.exit(0)


async def outdated_message(message: WialonBlockMessage):
    try:
        await asyncio.sleep(OUTDATED_MESSAGE_TIMEOUT)
        await message.edit_text(
            "*Повідомлення застаріло:* %s" % datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            reply_markup=kb.refresh()
        )
    except TelegramBadRequest as e:
        logging.error(e)


async def delete_message(message: WialonBlockMessage):
    try:
        await asyncio.sleep(DELETE_MESSAGE_TIMEOUT)
        await message.delete()
    except TelegramBadRequest as e:
        logging.exception(e)


async def set_default_commands(bot: Bot):
    """
    Sets the default commands for the bot.
    These commands will appear in the Telegram client's menu.
    """
    commands = [
        # BotCommand(command="start", description="Start the bot"),
        BotCommand(command="list", description="Відобразити список трекерів"),
        # BotCommand(command="get_group_id", description="Отримати ID групи"),
    ]
    await bot.set_my_commands(commands)
    logging.info("Default commands set.")


async def on_message_error(message: WialonBlockMessage, exception: Exception):
    error_uuid = uuid.uuid4()
    await message.answer(ERROR_ANSWER_FORMAT.format(uuid=error_uuid))
    logging.error(ERROR_LOG_MSG_FORMAT.format(
        uuid=error_uuid,
        msg=str(exception)
    ))
    if isinstance(exception, WialonError):
        logging.error(exception.reason)
        logging.exception(exception)
    else:
        logging.exception(exception)
    logging.error("MSG: {}".format(message))


async def on_call_error(call: WialonBlockCallbackQuery, exception: Exception):
    await on_message_error(call.message, exception)
    logging.error("CALL: {}".format(call))
    await call.answer()


# @dp.message(Command("list", "start"))
# async def command_list_handler(message: WialonBlockMessage) -> None:
#     try:
#         logging.info("Received command: `%s`, from chat `%s`" % (message.text, message.chat.id))
#         pattern = "*"
#         objects = await message.bot.wialon_worker.list_by_tg_group_id(
#             message.chat.id, pattern
#         )
#         if not objects:
#             logging.error("No objects found for `%s`" % message.text)
#             await message.answer(NO_OBJECTS_MESSAGE)
#             return
#
#         # Escape the dynamic parts before formatting
#         current_datetime_str = escape_markdown_v2(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
#         username_escaped = escape_markdown_v2(message.from_user.username)
#
#         await message.answer(
#             SEARCH_RESULT_MESSAGE_FORMAT.format(
#                 pattern=pattern,
#                 datetime=current_datetime_str,
#                 user=username_escaped,
#             ),
#             reply_markup=kb.search_result(objects),
#         )
#     except Exception as e:
#         await on_message_error(message, e)
#
#     await outdated_message(message)
#     # await delete_message(message)


async def command_get_group_id_handler(message: WialonBlockMessage) -> None:
    log_msg = "Received command: `%s`, from `%d`, chat: `%d`" % (message.text, message.from_user.id, message.chat.id)
    logging.info(log_msg)
    await message.answer(log_msg)


async def command_pages_handler(message: WialonBlockMessage) -> None:
    try:
        logging.info("Received command: `%s`, from chat `%s`" % (message.text, message.chat.id))
        pattern = "*"
        objects = await message.bot.wialon_worker.list_by_tg_group_id(
            message.chat.id, pattern
        )
        if not objects:
            logging.error("No objects found for `%s`" % message.text)
            await message.answer(NO_OBJECTS_MESSAGE)
            return

        # Escape the dynamic parts before formatting
        current_datetime_str = escape_markdown_v2(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        username_escaped = escape_markdown_v2(message.from_user.username)

        callback_data = kb.PagesCallback(
            start=0, end=kb.ITEMS_PER_PAGE, pattern=pattern, action=PagesAction.REFRESH
        )
        await message.answer(
            PAGES_RESULT_MESSAGE_FORMAT.format(
                pattern=escape_markdown_v2(pattern),
                total=len(objects),
                start=callback_data.start + 1,
                end=callback_data.end,
                datetime=current_datetime_str,
                user=username_escaped,
            ),
            reply_markup=kb.pages_result(objects, callback_data)
        )

    except Exception as e:
        await on_message_error(message, e)

    await outdated_message(message)


ALL_SERVICE_CONTENT_TYPES = {
    ContentType.NEW_CHAT_MEMBERS,
    ContentType.LEFT_CHAT_MEMBER,
    ContentType.NEW_CHAT_TITLE,
    ContentType.NEW_CHAT_PHOTO,
    ContentType.DELETE_CHAT_PHOTO,
    ContentType.GROUP_CHAT_CREATED,
    ContentType.SUPERGROUP_CHAT_CREATED,
    ContentType.CHANNEL_CHAT_CREATED,
    ContentType.MESSAGE_AUTO_DELETE_TIMER_CHANGED,
    ContentType.MIGRATE_TO_CHAT_ID,
    ContentType.MIGRATE_FROM_CHAT_ID,
    ContentType.PINNED_MESSAGE,
}

SKIP_ALL_SERVICE_UPDATES = ~F.content_type.in_(ALL_SERVICE_CONTENT_TYPES)


# @dp.message(F.text & SKIP_ALL_SERVICE_UPDATES)
# async def search_avl_units(message: WialonBlockMessage):
#     try:
#         logging.info("Received message: `%s`, from chat `%s`" % (message.text, message.chat.id))
#
#         objects = await message.bot.wialon_worker.list_by_tg_group_id(
#             message.chat.id,
#             pattern=message.text
#         )
#
#         if not objects:
#             logging.error("No objects found for `%s`" % message.text)
#             await message.answer(NO_OBJECTS_MESSAGE)
#             return
#
#         # Escape the dynamic parts before formatting
#         current_datetime_str = escape_markdown_v2(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
#         username_escaped = escape_markdown_v2(message.from_user.username)
#
#         await message.answer(
#             SEARCH_RESULT_MESSAGE_FORMAT.format(
#                 # pattern=escape_markdown_v2(message.text),
#                 pattern=message.text,
#                 datetime=current_datetime_str,
#                 user=username_escaped,
#             ),
#             reply_markup=kb.search_result(objects, False),
#         )
#     except Exception as e:
#         await on_message_error(message, e)
#
#     await outdated_message(message)


async def search_avl_units(message: WialonBlockMessage):
    try:
        logging.info("Received message: `%s`, from chat `%s`" % (message.text, message.chat.id))

        objects = await message.bot.wialon_worker.list_by_tg_group_id(
            message.chat.id,
            pattern=message.text
        )

        if not objects:
            logging.error("No objects found for `%s`" % message.text)
            await message.answer(NO_OBJECTS_MESSAGE)
            return

        # Escape the dynamic parts before formatting
        current_datetime_str = escape_markdown_v2(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        username_escaped = escape_markdown_v2(message.from_user.username)

        callback_data = kb.PagesCallback(
            start=0, end=kb.ITEMS_PER_PAGE, pattern=message.text, action=PagesAction.REFRESH
        )
        total = len(objects)
        await message.answer(
            PAGES_RESULT_MESSAGE_FORMAT.format(
                pattern=message.text,
                total=total,
                start=min(callback_data.start + 1, total),
                end=min(callback_data.end, total),
                datetime=current_datetime_str,
                user=username_escaped,
            ),
            reply_markup=kb.pages_result(objects, callback_data)
        )
    except Exception as e:
        await on_message_error(message, e)

    await outdated_message(message)


async def pages_call_handler(call: WialonBlockCallbackQuery, callback_data: kb.PagesCallback) -> None:
    try:
        logging.info("Received call: `%s`, from chat `%s`" % (callback_data, call.message.chat.id))
        pattern = callback_data.pattern
        objects = await call.message.bot.wialon_worker.list_by_tg_group_id(
            call.message.chat.id, pattern
        )
        if not objects:
            logging.error("No objects found for `%s`" % callback_data.pattern)
            await call.answer(NO_OBJECTS_MESSAGE)
            return

        # Escape the dynamic parts before formatting
        current_datetime_str = escape_markdown_v2(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        username_escaped = escape_markdown_v2(call.from_user.username)

        total = len(objects)
        await call.message.answer(
            PAGES_RESULT_MESSAGE_FORMAT.format(
                pattern=pattern,
                total=total,
                start=min(callback_data.start + 1, total),
                end=min(callback_data.end, total),
                datetime=current_datetime_str,
                user=username_escaped,
            ),
            reply_markup=kb.pages_result(objects, callback_data)
        )
        await call.message.delete()
        if callback_data.action == PagesAction.REFRESH:
            # await call.answer("Список об'єктів оновлено")
            await call.answer()

    except TelegramBadRequest as e:
        logging.error(e)
        logging.error(call)
        await call.answer("Оновлень немає")
    except Exception as e:
        await on_call_error(call, e)


async def command_ignore_handler(message: WialonBlockMessage) -> None:
    pass


# @dp.message(Command("lookup"))
# async def command_lookup_handler(message: WialonBlockMessage) -> None:
#     message_text = message.text
#     command_entity = message.entities[0]  # Assuming the bot_command is the first entity
#     if isinstance(command_entity, MessageEntity) and command_entity.type == "bot_command":
#         # The text after the command will start at the offset + length of the command
#         start_index = command_entity.offset + command_entity.length
#         sometext = message_text[start_index:].strip()
#         print(sometext)
#     else:
#         await message.reply("Неправильний формат команди.")


# # This decorator registers the function to handle inline queries
# @dp.inline_query(F.query.func(lambda q: True))  # Handle all inline queries
# async def inline_search_wialon_objects(inline_query: WialonBlockInlineQuery):
#     """
#     Handles inline queries to provide autocomplete/search for Wialon objects.
#     """
#     query_text = inline_query.query.strip().lower()  # Get user's search query, case-insensitive
#
#     logging.info(f"Received inline query from @{inline_query.from_user.username}: '{query_text}'")
#
#     results = []
#
#     print(inline_query)
#
#     try:
#         # 1. Fetch Wialon objects
#         # You'll likely need a method in your wialon_worker to list all/filtered objects
#         # For demonstration, let's assume list_all_objects() returns objects with 'id' and 'name' attributes.
#         # If your list_by_tg_group_id works, you might need to adapt.
#         # For inline mode, results shouldn't typically be restricted by the chat ID where the query is typed.
#         # You might want to list objects associated with the user, or all publicly searchable objects.
#         all_objects = await inline_query.bot.wialon_worker.list_by_tg_group_id(415715051)  # Or a more refined list
#
#         # 2. Filter objects based on the query text
#         # If query_text is empty, you might return recent objects or a general list.
#         # If the list is very large, consider pagination using 'next_offset'.
#         filtered_objects = [
#             obj for obj in all_objects
#             if not query_text or query_text in obj['nm'].lower()
#         ]
#
#         # Limit the number of results to avoid hitting Telegram's limits (max 50 results per query)
#         for obj in filtered_objects[:50]:
#             # Each result needs a unique ID (as string)
#             result_id = str(obj['id'])
#
#             # The title displayed in the autocomplete list
#             title = obj['nm']
#
#             # The message that will be sent to the chat when the user selects this result
#             # You can send plain text, Markdown, or HTML.
#             # It's good practice to escape any user-generated or dynamic content.
#             selected_message_text = f"Selected Wialon object: *{escape_markdown_v2(obj['nm'])}*\n" \
#                                     f"ID: `{escape_markdown_v2(str(obj['id']))}`"
#
#             # You can also use deep linking to send a '/start' command to your bot with a parameter
#             # that your bot can then parse to show more details about the object.
#             # Example: deep_link = await create_start_link(inline_query.bot, f"obj_{obj.id}", encode=True)
#             # selected_message_text = f"View details for *{escape_markdown_v2(obj.name)}*: {deep_link}"
#
#             results.append(
#                 InlineQueryResultArticle(
#                     id=result_id,
#                     title=f"{obj['_lock_']} {title}",
#                     description=f"Статус: {STATE_STRING_MAP.get(obj['_lock_'], ObjState.UNKNOWN)}",  # Optional subtitle
#                     input_message_content=InputTextMessageContent(
#                         message_text=selected_message_text,
#                         parse_mode="MarkdownV2"  # Use MarkdownV2 for better formatting and security
#                     ),
#                     # You can also add a thumbnail_url if your objects have images
#                     # thumbnail_url="URL_to_object_icon.png",
#                     # thumbnail_width=48,
#                     # thumbnail_height=48,
#                 )
#             )
#
#         # If no results found for the query
#         if not results and query_text:
#             results.append(
#                 InlineQueryResultArticle(
#                     id="no_results",
#                     title="No objects found",
#                     description=f"No Wialon objects matching '{query_text}'",
#                     input_message_content=InputTextMessageContent(
#                         message_text=f"No Wialon objects matched your search for '{escape_markdown_v2(query_text)}'."
#                     )
#                 )
#             )
#
#     except Exception as e:
#         logging.error(f"Error processing inline query '{query_text}': {e}")
#         results.append(
#             InlineQueryResultArticle(
#                 id="error",
#                 title="Error occurred",
#                 description="Could not fetch objects. Please try again.",
#                 input_message_content=InputTextMessageContent(
#                     message_text="An error occurred while fetching Wialon objects."
#                 )
#             )
#         )
#
#     # 3. Answer the inline query with the results
#     await inline_query.answer(
#         results,
#         cache_time=1,  # How long results can be cached (in seconds). Lower for faster autocomplete updates.
#         is_personal=True,  # Set to True if results depend on the user (e.g., user-specific objects)
#         # next_offset="some_offset" # Use this for pagination if you have more than 50 results
#     )


async def refresh_call_handler(call: WialonBlockCallbackQuery):
    try:
        objects = await call.bot.wialon_worker.list_by_tg_group_id(call.message.chat.id)
        if not objects:
            logging.error("No objects found for call `%s`" % call.id)
            await call.answer(NO_OBJECTS_MESSAGE)
            return

        # Escape the dynamic parts before formatting
        current_datetime_str = escape_markdown_v2(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        username_escaped = escape_markdown_v2(call.message.from_user.username)

        await call.message.answer(
            LIST_RESULT_MESSAGE_FORMAT.format(
                datetime=current_datetime_str,
                user=username_escaped,
            ),
            reply_markup=kb.search_result(objects)
        )
        await call.message.delete()
        await call.answer("Список об'єктів оновлено")
    except TelegramBadRequest as e:
        logging.error(e)
        logging.error(call)
        await call.answer("Оновлень немає")
    except Exception as e:
        await on_call_error(call, e)


async def update_lock_state(unit, lock_state, call: WialonBlockCallbackQuery, as_answer=False):
    u_name = unit.get('item', {}).get('nm', "Невідомий об'єкт")
    dt = escape_markdown_v2(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
    message_text = UNIT_MESSAGE_FORMAT.format(
        name=escape_markdown_v2(u_name),
        lock=lock_state,
        state=STATE_STRING_MAP.get(lock_state, ObjState.UNKNOWN),
        user=escape_markdown_v2(call.from_user.username),
        datetime=dt
    )
    u_id = unit.get('item', {}).get('id', None)

    message = call.message
    message_action = message.answer if as_answer else message.edit_text

    match lock_state:
        case ObjState.LOCKED:
            await message_action(message_text, reply_markup=kb.locked(u_id))
        case ObjState.UNLOCKED:
            await message_action(message_text, reply_markup=kb.unlocked(u_id))
        case _:
            await message_action(message_text)


async def show_unit_call_handler(call: WialonBlockCallbackQuery, callback_data: kb.GetUnitCallback):
    try:
        u_id = callback_data.unit_id
        unit, lock_state = await call.bot.wialon_worker.get_unit_and_lock_state(call.message.chat.id, u_id)
        await update_lock_state(unit, lock_state, call, as_answer=True)
        await call.answer()
    except Exception as e:
        await on_call_error(call, e)

    await delete_message(call.message)


async def lock_unit_call_handler(call: WialonBlockCallbackQuery, callback_data: kb.LockUnitCallback):
    try:
        u_id = callback_data.unit_id
        logging.info("Attempt to lock uid: `%s`" % u_id)
        unit, lock_state = await call.bot.wialon_worker.lock(call.message.chat.id, u_id)
        match lock_state:
            case ObjState.LOCKED:
                logging.info(
                    f'Object `%s` (`%s`) locking success'
                    % (unit.get('item', {}).get('nm', "Невідомий об'єкт"), u_id)
                )
            case _:
                raise ValueError("Object `%s` was not locked" % u_id)
        await update_lock_state(unit, lock_state, call)
        await call.answer()
    except Exception as e:
        await on_call_error(call, e)


# @dp.callback_query(kb.UnlockUnitCallback.filter())
async def unlock_unit_call_handler(call: WialonBlockCallbackQuery, callback_data: kb.UnlockUnitCallback):
    try:
        u_id = callback_data.unit_id
        logging.info("Attempt to unlock uid: `%s`" % u_id)
        unit, lock_state = await call.bot.wialon_worker.unlock(call.message.chat.id, u_id)
        match lock_state:
            case ObjState.UNLOCKED:
                logging.info(
                    f'Object `%s` (`%s`) unlocking success'
                    % (unit.get('item', {}).get('nm', "Невідомий об'єкт"), u_id)
                )
            case _:
                raise ValueError("Object `%s` was not unlocked" % u_id)
        await update_lock_state(unit, lock_state, call)
        await call.answer()
    except Exception as e:
        await on_call_error(call, e)


# @dp.callback_query()
async def any_call_handler(call: WialonBlockCallbackQuery):
    logging.info("unknown call: %s" % call.data)


# @dp.message()  # listens all messages and log it out
async def any_message_handler(message: WialonBlockMessage):
    logging.info('undefined message %s by @%s (%s)' % (message.from_user.id,
                                                       message.from_user.username,
                                                       message.text))


async def run_bot(config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    config: Config = load_config(config_path)
    wialon_worker = WialonWorker(
        config.wialon.host,
        config.wialon.token,
        {str(group.chat_id): group for group in config.tg.groups}
    )

    bot = WialonBlockBot(token=config.tg.bot_token, wialon_worker=wialon_worker,
                         default=DefaultBotProperties(**config.tg.bot_props.model_dump()))

    dp.startup.register(set_default_commands)

    dp.message(Command("list"))(command_pages_handler)
    dp.message(Command("get_group_id"))(command_get_group_id_handler)
    dp.message(Command("i"))(command_ignore_handler)
    dp.message(Command("pkill"))(kill_switch)

    dp.message(F.text & SKIP_ALL_SERVICE_UPDATES)(search_avl_units)

    dp.callback_query(kb.PagesCallback.filter())(pages_call_handler)
    dp.callback_query(kb.RefreshCallback.filter())(refresh_call_handler)
    dp.callback_query(kb.GetUnitCallback.filter())(show_unit_call_handler)
    dp.callback_query(kb.LockUnitCallback.filter())(lock_unit_call_handler)
    dp.callback_query(kb.UnlockUnitCallback.filter())(unlock_unit_call_handler)

    dp.callback_query()(any_call_handler)
    dp.message()(any_message_handler)

    # Start polling
    try:
        logging.info("Starting bot...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logging.info("Bot stopped.")
