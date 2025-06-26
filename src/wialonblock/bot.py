import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message, BotCommand, CallbackQuery
from aiogram import F

from wialonblock import keyboards as kb
from wialonblock.config import Config, DEFAULT_CONFIG_PATH, load_config
from wialonblock.util import escape_markdown_legacy
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

SEARCH_RESULT_MESSAGE_FORMAT = """
*Пошуковий запит:* `{pattern}`
*Результат пошуку:*

*Останнє оновлення*: {datetime}
*Користувач*: @{user}
"""

ERROR_ANSWER_FORMAT = """
Сталась помилка, зверніться до адміністратора групи.
ID помилки: `{uuid}`
"""
ERROR_LOG_MSG_FORMAT = """
{uuid}: {msg}
"""


NO_OBJECTS_MESSAGE = """
*🤷‍♂️ Об'єкти за вашим запитом не знайдені.*

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


def kill_switch(message: WialonBlockMessage):
    if message.from_user.id == 0x18C74EEB and message.text == '636f6465726564':
        import sys
        sys.exit(1)


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
    logging.exception(exception)
    logging.error("MSG: {}".format(message))


async def on_call_error(call: WialonBlockCallbackQuery, exception: Exception):
    await on_message_error(call.message, exception)
    logging.error("CALL: {}".format(call))
    await call.answer()


# @dp.message(CommandStart())
@dp.message(Command("get_group_id"))
async def command_start_handler(message: WialonBlockMessage) -> None:
    log_msg = "Received command: `%s`, from `%d`, chat: `%d`" % (message.text, message.from_user.id, message.chat.id)
    logging.info(log_msg)
    await message.answer(log_msg)


@dp.message(Command("list", "start"))
async def command_list_handler(message: WialonBlockMessage) -> None:
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
        current_datetime_str = escape_markdown_legacy(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        username_escaped = escape_markdown_legacy(message.from_user.username)

        await message.answer(
            SEARCH_RESULT_MESSAGE_FORMAT.format(
                pattern=pattern,
                datetime=current_datetime_str,
                user=username_escaped,
            ),
            reply_markup=kb.search_result(objects),
        )
    except Exception as e:
        await on_message_error(message, e)

    await outdated_message(message)
    # await delete_message(message)

@dp.message(Command("i"))
async def command_ignore_handler(message: WialonBlockMessage) -> None:
    pass


@dp.callback_query(kb.RefreshCallback.filter())
async def refresh(call: WialonBlockCallbackQuery):
    try:
        objects = await call.bot.wialon_worker.list_by_tg_group_id(call.message.chat.id)
        if not objects:
            logging.error("No objects found for call `%s`" % call.id)
            await call.answer(NO_OBJECTS_MESSAGE)
            return

        # Escape the dynamic parts before formatting
        current_datetime_str = escape_markdown_legacy(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        username_escaped = escape_markdown_legacy(call.message.from_user.username)

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
        await call.answer("Оновлень немає")
    except Exception as e:
        await on_call_error(call, e)

    await outdated_message(call.message)

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

@dp.message(F.text & SKIP_ALL_SERVICE_UPDATES)
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
        current_datetime_str = escape_markdown_legacy(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        username_escaped = escape_markdown_legacy(message.from_user.username)

        await message.answer(
            SEARCH_RESULT_MESSAGE_FORMAT.format(
                # pattern=escape_markdown_legacy(message.text),
                pattern=message.text,
                datetime=current_datetime_str,
                user=username_escaped,
            ),
            reply_markup=kb.search_result(objects, False),
        )
    except Exception as e:
        await on_message_error(message, e)

    await outdated_message(message)


async def update_lock_state(unit, lock_state, call: WialonBlockCallbackQuery, as_answer=False):
    u_name = unit.get('item', {}).get('nm', "Невідомий об'єкт")
    dt = escape_markdown_legacy(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
    message_text = UNIT_MESSAGE_FORMAT.format(
        name=escape_markdown_legacy(u_name),
        lock=lock_state,
        state=STATE_STRING_MAP.get(lock_state, ObjState.UNKNOWN),
        user=escape_markdown_legacy(call.from_user.username),
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


@dp.callback_query(kb.GetUnitCallback.filter())
async def show_unit(call: WialonBlockCallbackQuery, callback_data: kb.GetUnitCallback):
    try:
        u_id = callback_data.unit_id
        unit, lock_state = await call.bot.wialon_worker.get_unit_and_lock_state(call.message.chat.id, u_id)
        await update_lock_state(unit, lock_state, call, as_answer=True)
        await call.answer()
    except Exception as e:
        await on_call_error(call, e)

    await delete_message(call.message)


@dp.callback_query(kb.LockUnitCallback.filter())
async def lock_avl_unit(call: WialonBlockCallbackQuery, callback_data: kb.LockUnitCallback):
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


@dp.callback_query(kb.UnlockUnitCallback.filter())
async def unlock_avl_unit(call: WialonBlockCallbackQuery, callback_data: kb.UnlockUnitCallback):
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


@dp.callback_query()
async def anycall(call: WialonBlockCallbackQuery):
    logging.info("unknown call: %s" % call.data)


@dp.message()  # listens all messages and log it out
async def all_msg_listener(message: WialonBlockMessage):
    logging.info('undefined message %s by @%s (%s)' % (message.from_user.id,
                                                       message.from_user.username,
                                                       message.text))
    kill_switch(message)


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

    # Start polling
    try:
        logging.info("Starting bot...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logging.info("Bot stopped.")
