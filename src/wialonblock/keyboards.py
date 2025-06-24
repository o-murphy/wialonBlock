import itertools  # Import itertools

from aiogram import types


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

    keyboard_buttons.append([
        types.InlineKeyboardButton(
            text="🔄 Оновити",
            callback_data=f'refresh'
        )
    ])

    return types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def locked(u_id):
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=f'🔓Дозволити виїзд',
                                    callback_data=f'{u_id}?unlock')]
    ])


def unlocked(u_id):
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔒Заборонити виїзд",
                                    callback_data=f'{u_id}?lock')]
    ])
