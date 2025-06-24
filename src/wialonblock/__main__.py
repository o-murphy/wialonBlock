import asyncio
import logging
import sys

import tomllib
from typing import Dict, Any

from wialonblock.bot import run_bot

ENV_TOML_PATH = ".env.toml"
logging.basicConfig(level=logging.INFO, stream=sys.stdout)


async def run():
    with open(ENV_TOML_PATH, 'rb') as fp:
        ENV = tomllib.load(fp)

    bot_task = run_bot(token=ENV['tg_bot_token'], **ENV['tg_bot_props'])
    await asyncio.gather(bot_task)

def main():
    asyncio.run(run())

if __name__ == "__main__":
    asyncio.run(run())