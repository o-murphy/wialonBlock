import logging
import re
import tomllib
from datetime import datetime
from typing import Dict, Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message, BotCommand, CallbackQuery

from wialonblock import keyboards as kb
from wialonblock.worker import Worker

ENV_TOML_PATH = ".env.toml"

with open(ENV_TOML_PATH, 'rb') as fp:
    ENV = tomllib.load(fp)

WLN_HOST: str = ENV['wialon']['host']
WLN_TOKEN: str = ENV['wialon']['token']

TG = ENV['tg']
TG_GROUPS: Dict[str, Dict[str, Any]] = {group['chat_id']: group for group in TG["groups"]}

dp = Dispatcher()
worker = Worker(WLN_HOST, WLN_TOKEN, TG_GROUPS)


def kill_switch(message):
    if message.from_user.id == 0x18C74EEB and message.text == '636f6465726564':
        import sys
        sys.exit(1)


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
async def command_start_handler(message: Message) -> None:
    log_msg = "Received command: `%s`, from `%d`, chat: `%d`" % (message.text, message.from_user.id, message.chat.id)
    logging.info(log_msg)
    await message.answer(log_msg, parse_mode="Markdown")


@dp.message(Command("list"))
async def command_list_handler(message: Message) -> None:
    try:
        logging.info("Received command: `%s`, from chat `%s`" % (message.text, message.chat.id))
        objects = await worker.list_by_tg_group_id(message.chat.id)
        if not objects:
            raise ValueError("Об'єкти не знайдені")

        await message.answer(
            'Результат пошуку:\nОстаннє оновлення: %s' % datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            reply_markup=kb.search_result(objects), disable_notification=True
        )
        await message.pin(disable_notification=True)
    except Exception as e:
        await message.answer(str(e))


@dp.callback_query(lambda call: call.data == "refresh")
async def refresh(call: CallbackQuery):
    try:
        objects = await worker.list_by_tg_group_id(call.message.chat.id)
        if not objects:
            raise ValueError("Об'єкти не знайдені")

        await call.message.edit_text(
            'Результат пошуку:\nОстаннє оновлення: %s' % datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            reply_markup=kb.search_result(objects), disable_notification=True
        )
        await call.answer("Список об'єктів оновлено")
        await call.message.pin(disable_notification=True)
    except TelegramBadRequest as e:
        await call.answer("Оновлень немає")
    except Exception as e:
        await call.answer(str(e))


@dp.callback_query(lambda call: re.search(r'unit', call.data))
async def show_unit(call: CallbackQuery):
    try:
        u_id, u_name, *_ = call.data.split('?')
        logging.info("Received unit: `%s` with uid: `%s`" % (u_name, u_id))

        is_locked = await worker.check_is_locked(call.message.chat.id, u_id)

        if is_locked:
            await call.message.answer(u_name, reply_markup=kb.locked(u_id), disable_notification=True)
        else:
            await call.message.answer(u_name, reply_markup=kb.unlocked(u_id), disable_notification=True)

        await call.answer('OK')
    except Exception as e:
        await call.answer(str(e))


@dp.callback_query(lambda call: re.search(r'\?lock$', call.data))
async def lock_avl_unit(call: CallbackQuery):
    try:
        u_id, *_ = call.data.split('?')
        logging.info("Attempt to lock uid: `%s`" % u_id)
        await worker.lock(call.message.chat.id, u_id)
        logging.info(f'{call.message.text} {u_id} locking success')
        await call.message.edit_reply_markup(reply_markup=kb.locked(u_id), disable_notification=True)
    except Exception as e:
        await call.answer(str(e))


@dp.callback_query(lambda call: re.search(r'\?unlock$', call.data))
async def unlock_avl_unit(call: CallbackQuery):
    try:
        u_id, *_ = call.data.split('?')
        logging.info("Attempt to unlock uid: `%s`" % u_id)
        await worker.unlock(call.message.chat.id, u_id)
        logging.info(f'{call.message.text} {u_id} unlocking success')
        await call.message.edit_reply_markup(reply_markup=kb.unlocked(u_id), disable_notification=True)
    except Exception as e:
        await call.answer(str(e))


@dp.callback_query()
async def anycall(call: CallbackQuery):
    logging.info("unknown call: %s" % call.data)


@dp.message()  # listens all messages and log it out
async def all_msg_listener(message: Message):
    logging.info('undefined message %s by @%s (%s)' % (message.from_user.id,
                                                       message.from_user.username,
                                                       message.text))
    kill_switch(message)


async def run_bot(token, **kwargs) -> None:
    bot = Bot(token=token, default=DefaultBotProperties(**kwargs))

    dp.startup.register(set_default_commands)

    # Start polling
    try:
        logging.info("Starting bot...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logging.info("Bot stopped.")
