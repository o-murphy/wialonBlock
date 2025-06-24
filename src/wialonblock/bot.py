import logging
import tomllib
from typing import Dict, Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message, BotCommand

from wialonblock.worker import Worker
from wialonblock import keyboards as kb

ENV_TOML_PATH = ".env.toml"

with open(ENV_TOML_PATH, 'rb') as fp:
    ENV = tomllib.load(fp)

WLN_HOST: str = ENV['wln_host']
TG_GROUPS: Dict[str, Dict[str, Any]] = {group['tg_bot_chat_id']: group for group in ENV["tg_groups"]}

dp = Dispatcher()
worker = Worker(WLN_HOST, TG_GROUPS)


async def set_default_commands(bot: Bot):
    """
    Sets the default commands for the bot.
    These commands will appear in the Telegram client's menu.
    """
    commands = [
        # BotCommand(command="start", description="Start the bot"),
        BotCommand(command="list", description="Display all trackers"),
        BotCommand(command="getchat", description="Get chan id"),
    ]
    await bot.set_my_commands(commands)
    logging.info("Default commands set.")


# @dp.message(CommandStart())
@dp.message(Command("getchat"))
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
            'Результат пошуку:',
            reply_markup=kb.search_result(objects)
        )
    except Exception as e:
        await message.answer(str(e))


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
