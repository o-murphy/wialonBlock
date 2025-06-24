import re
import tomllib
from pathlib import Path
from typing import Optional, List, Literal

from pydantic import BaseModel, field_validator  # Updated imports for v2 validators

DEFAULT_CONFIG_PATH = Path(".env.toml")

# Regular expression for Telegram bot token
TELEGRAM_TOKEN_PATTERN = r'^\d+:[a-zA-Z0-9_-]{35}$'

# Regular expression for Wialon token
WIALON_TOKEN_PATTERN = r'^[a-fA-F0-9]{72}$'

# Regular expression for Telegram username
# Starts with a letter, can contain letters, numbers, underscores, length 5-32
TELEGRAM_USERNAME_PATTERN = r'^t.me/[a-zA-Z][a-zA-Z0-9_]{4,31}$'


class BotProps(BaseModel):
    """Модель для властивостей бота."""
    disable_notification: bool
    parse_mode: Literal["html", "markdown", "markdownv2"]


class TelegramGroup(BaseModel):
    """Модель для конфігурації групи Telegram."""
    tag: Optional[str] = ""
    chat_name: Optional[str] = ""
    chat_id: str  # Telegram chat IDs can be very long, often represented as strings
    wln_group_locked: str
    wln_group_unlocked: str
    wln_group_ignored: Optional[str] = ""


class TelegramConfig(BaseModel):
    """Модель для конфігурації Telegram."""
    bot_name: str
    # In Pydantic v2, `pattern` is still available on Field, but `field_validator` is the preferred way
    # for more complex or multiple validations. We'll use field_validator for both.
    bot_token: str

    bot_props: BotProps
    groups: List[TelegramGroup]

    # Pydantic v2 uses @field_validator instead of @validator
    @field_validator('bot_name')
    @classmethod  # @classmethod is required for field_validator
    def validate_bot_name_format(cls, v: str):
        if not re.fullmatch(TELEGRAM_USERNAME_PATTERN, v):
            raise ValueError(f'Invalid Telegram username format in bot_name: "{v}"')
        return v

    @field_validator('bot_token')
    @classmethod  # @classmethod is required for field_validator
    def validate_telegram_token(cls, v: str):
        if not re.fullmatch(TELEGRAM_TOKEN_PATTERN, v):
            raise ValueError('Invalid Telegram bot token format')
        return v


class WialonConfig(BaseModel):
    """Модель для конфігурації Wialon."""
    host: str  # HttpUrl works great in Pydantic v2
    token: str

    @field_validator('token')
    @classmethod  # @classmethod is required for field_validator
    def validate_wialon_token(cls, v: str):
        if not re.fullmatch(WIALON_TOKEN_PATTERN, v):
            raise ValueError('Invalid Wialon token format')
        return v


class Config(BaseModel):
    """Головна модель конфігурації."""
    tg: TelegramConfig
    wialon: WialonConfig


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    with open(path, 'rb') as fp:
        env = tomllib.load(fp)
    return Config.model_validate(env)


if __name__ == '__main__':
    print(load_config(Path('../../.env.toml')))

# # --- Приклад використання ---
# if __name__ == "__main__":
#     import toml
#     import json
#
#     toml_string_valid = """
# tg.bot_name = "t.me/wialonblockbot"
# tg.bot_token = "7804428474:AAEVnAf9F-dOJSk7SOl847DTKLa5E5iPafc"
#
# [wialon]
# host = "https://local.gpshub.pro"
# token = "3b1b9d108ff756a9e2a7fbc4445e31af4D169D35140B6F0DD05CBD3187B94AB468EA88A0"
#
# [tg.bot_props]
# disable_notification = true
# parse_mode = "html"
#
# [[tg.groups]]
# tag = "kyiv"
# chat_name = "Kyiv"
# chat_id = "-1002561088191"
# wln_group_locked = "Autoblock_Kyiv_ON"
# wln_group_unlocked = "Autoblock_Kyiv_OFF"
# wln_group_ignored = ""
#
# [[tg.groups]]
# tag = "lviv"
# chat_name = "Lviv"
# chat_id = "-1001234567890"
# wln_group_locked = "Autoblock_Lviv_ON"
# wln_group_unlocked = "Autoblock_Lviv_OFF"
# wln_group_ignored = "some_ignored_group"
#     """
#
#     toml_string_invalid_bot_name = """
# tg.bot_name = "t.me/invalid" # Закоротке ім'я користувача
# tg.bot_token = "7804428474:AAEVnAf9F-dOJSk7SOl847DTKLa5E5iPafc"
#
# [wialon]
# host = "https://local.gpshub.pro"
# token = "3b1b9d108ff756a9e2a7fbc4445e31af4D169D35140B6F0DD05CBD3187B94AB468EA88A0"
#
# [tg.bot_props]
# disable_notification = true
# parse_mode = "html"
#
# [[tg.groups]]
# tag = "kyiv"
# chat_name = "Kyiv"
# chat_id = "-1002561088191"
# wln_group_locked = "Autoblock_Kyiv_ON"
# wln_group_unlocked = "Autoblock_Kyiv_OFF"
# wln_group_ignored = ""
#     """
#
#     print("--- Валідна конфігурація ---")
#     try:
#         parsed_toml = toml.loads(toml_string_valid)
#         config = Config.model_validate(parsed_toml)
#         print("Конфігурація успішно провалідована!")
#     except Exception as e:
#         print(f"Помилка валідації:\n{e}")
#         # print(json.dumps(e.errors(), indent=2))
#
#     print("\n--- Невалідна конфігурація (bot_name) ---")
#     try:
#         parsed_toml_invalid_bot_name = toml.loads(toml_string_invalid_bot_name)
#         config_invalid_bot_name = Config.model_validate(parsed_toml_invalid_bot_name)
#     except Exception as e:
#         print(f"Помилка валідації (bot_name):\n{e}")
#         # print(json.dumps(e.errors(), indent=2))
