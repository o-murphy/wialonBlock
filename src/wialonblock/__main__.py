import asyncio
import logging
import sys

from wialonblock.bot import run_bot
from wialonblock.config import load_config

logging.basicConfig(level=logging.INFO, stream=sys.stdout)


async def run():
    config = load_config()
    bot_task = run_bot(config)
    await asyncio.gather(bot_task)


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
