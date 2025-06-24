import asyncio
import logging
import sys

import tomllib
from typing import Dict, Any

from wialonblock.bot import run_bot

ENV_TOML_PATH = ".env.toml"
logging.basicConfig(level=logging.INFO, stream=sys.stdout)


async def run(env):
    tg_conf = env['tg']
    bot_task = run_bot(token=tg_conf['bot_token'], **tg_conf['bot_props'])
    await asyncio.gather(bot_task)

def main():
    with open(ENV_TOML_PATH, 'rb') as fp:
        env = tomllib.load(fp)
    asyncio.run(run(env))

if __name__ == "__main__":
    main()
