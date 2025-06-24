import asyncio
import logging
import sys
from argparse import ArgumentParser
from pathlib import Path

from wialonblock.bot import run_bot
from wialonblock.config import DEFAULT_CONFIG_PATH

logging.basicConfig(level=logging.INFO, stream=sys.stdout)


async def run():
    parser = ArgumentParser(
        "wialonblock",
        description="A bot that allows you to block wialon objects",
    )
    parser.add_argument("config", type=Path, action="store", nargs='?',
                        help="Path to the TOML configuration file for WialonBlock bot.",
                        metavar="FILE_PATH", default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()
    await run_bot(config_path=args.config)


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
