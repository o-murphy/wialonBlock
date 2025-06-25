import itertools  # Import itertools

from aiogram import types
from aiogram.filters.callback_data import CallbackData

from wialonblock.worker import ObjState


class RefreshCallback(CallbackData, prefix="refresh"):
    pass


class GetUnitCallback(CallbackData, prefix="get_unit"):
    unit_id: int


class LockUnitCallback(CallbackData, prefix="lock_unit"):
    unit_id: int


class UnlockUnitCallback(CallbackData, prefix="unlock_unit"):
    unit_id: int


REFRESH_BUTTON = types.InlineKeyboardButton(
    text="🔄 Оновити",
    callback_data=RefreshCallback().pack()
)


def refresh():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[[REFRESH_BUTTON]]
    )


def search_result(items):
    keyboard_buttons = []

    # Use itertools.batched to group items into chunks of 2
    for batch in itertools.batched(items, 2):
        row = []
        for i in batch:
            lock = i.get("_lock_", ObjState.UNKNOWN)
            uid = i["id"]
            button = types.InlineKeyboardButton(
                text=f"{lock} {uid}",
                callback_data=GetUnitCallback(unit_id=uid).pack()
            )
            row.append(button)
        keyboard_buttons.append(row)

    keyboard_buttons.append([REFRESH_BUTTON])

    return types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def locked(u_id):
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text=f'{ObjState.UNLOCKED} Дозволити виїзд',
                callback_data=UnlockUnitCallback(unit_id=u_id).pack()
            )
        ]
    ])


def unlocked(u_id):
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text=f"{ObjState.LOCKED} Заборонити виїзд",
                callback_data=LockUnitCallback(unit_id=u_id).pack()
            )
        ]
    ])
