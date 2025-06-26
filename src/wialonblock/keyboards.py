import itertools  # Import itertools
from enum import StrEnum
from typing import Dict

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


def search_result(items, refresh=True):
    keyboard_buttons = []

    # Use itertools.batched to group items into chunks of 2
    for batch in itertools.batched(items, 2):
        row = []
        for i in batch:
            lock = i.get("_lock_", ObjState.UNKNOWN)
            uid = i["id"]
            uname = i["nm"]
            button = types.InlineKeyboardButton(
                text=f"{lock} {uname}",
                callback_data=GetUnitCallback(unit_id=uid).pack()
            )
            row.append(button)
        keyboard_buttons.append(row)

    if refresh:
        keyboard_buttons.append([REFRESH_BUTTON])

    return types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


class PagesAction(StrEnum):
    REFRESH = "🔄"
    BACK = "⬅️"
    NEXT = "➡️"

class PagesCallback(CallbackData, prefix="page"): # Changed prefix to 'page' for clarity, adjust if 'refresh' is specifically needed
    start: int
    end: int
    pattern: str # You have a 'pattern' field, ensure it's handled if it affects pagination logic
    action: PagesAction

ITEMS_PER_PAGE = 20

def next_page_button(current_page_data: PagesCallback, total_items_count: int):
    # Calculate the new start and end for the NEXT page
    new_start = current_page_data.start + ITEMS_PER_PAGE
    new_end = current_page_data.end + ITEMS_PER_PAGE

    # Ensure we don't go beyond the total items count
    # The 'start' of the last page should be calculated based on total_items_count
    # to avoid showing an empty page if total_items_count is not a multiple of ITEMS_PER_PAGE
    if new_start >= total_items_count:
        if total_items_count > 0:
            # Calculate the start of the last possible page
            new_start = max(0, (total_items_count - 1) // ITEMS_PER_PAGE * ITEMS_PER_PAGE)
        else:
            new_start = 0 # No items, so start is 0

    new_end = min(new_start + ITEMS_PER_PAGE, total_items_count)

    # Create a NEW PagesCallback instance with the updated data
    # The 'pattern' field is carried over as it's part of the CallbackData
    next_data = PagesCallback(
        start=new_start,
        end=new_end,
        pattern=current_page_data.pattern,
        action=PagesAction.NEXT
    )

    return types.InlineKeyboardButton(
        text=f"Далі {PagesAction.NEXT}",
        callback_data=next_data.pack()
    )

def back_page_button(current_page_data: PagesCallback):
    # Calculate the new start and end for the BACK page
    new_start = current_page_data.start - ITEMS_PER_PAGE
    new_end = current_page_data.end - ITEMS_PER_PAGE

    # Ensure start doesn't go below 0
    if new_start < 0:
        new_start = 0

    # Ensure end is adjusted correctly for the new start position
    new_end = min(new_start + ITEMS_PER_PAGE, current_page_data.start) # Use current_page_data.start as upper bound for end if going back from a partial page

    # If new_end ends up being 0 when new_start is 0 but there are items
    if new_start == 0 and new_end == 0 and ITEMS_PER_PAGE > 0:
        new_end = ITEMS_PER_PAGE

    # Create a NEW PagesCallback instance with the updated data
    back_data = PagesCallback(
        start=new_start,
        end=new_end,
        pattern=current_page_data.pattern,
        action=PagesAction.BACK
    )

    print(f"Back button data: {back_data}")
    return types.InlineKeyboardButton(
        text=f"{PagesAction.BACK} Назад",
        callback_data=back_data.pack()
    )

def refresh_page_button(current_page_data: PagesCallback):
    # For refresh, we want to keep the current page state but explicitly set action to REFRESH
    # This ensures that when the callback is handled, the state is re-evaluated.
    refresh_data = PagesCallback(
        start=current_page_data.start,
        end=current_page_data.end,
        pattern=current_page_data.pattern,
        action=PagesAction.REFRESH
    )
    print(f"Refresh button data: {refresh_data}")
    return types.InlineKeyboardButton(
        text="🔄 Оновити",
        callback_data=refresh_data.pack()
    )

def pages_result(items: Dict, prev_data: PagesCallback):
    keyboard_buttons = []
    total_items = len(items)

    # Determine the actual start and end for the current page being displayed.
    current_start = prev_data.start
    current_end = prev_data.end

    # --- MODIFICATION STARTS HERE ---
    # Only reset to first page if the current page is completely out of bounds
    # or if there are no items at all.
    # The 'REFRESH' action itself will now just re-render the *current* page
    # based on the incoming prev_data.start and prev_data.end.

    # Ensure start is within valid bounds after refresh or navigation
    current_start = max(0, min(current_start, total_items))

    # If the calculated start is beyond the available items, adjust to the last possible page start
    if current_start >= total_items and total_items > 0:
        current_start = max(0, (total_items - 1) // ITEMS_PER_PAGE * ITEMS_PER_PAGE)
    elif total_items == 0:
        current_start = 0

    current_end = min(current_start + ITEMS_PER_PAGE, total_items)

    # Handle case where current_start and current_end might be 0 but there are items
    # e.g., if total_items became 5 but prev_data was for page 0-20.
    if current_start == 0 and current_end == 0 and total_items > 0:
        current_end = min(ITEMS_PER_PAGE, total_items)
    # --- MODIFICATION ENDS HERE ---

    print(f"ITEMS LEN: {total_items}, Displaying from: {current_start} to {current_end}")

    items_to_display = items[current_start:current_end]

    for batch in itertools.batched(items_to_display, 2):
        row = []
        for i in batch:
            lock = i.get("_lock_", ObjState.UNKNOWN)
            uid = i["id"]
            uname = i["nm"]
            button = types.InlineKeyboardButton(
                text=f"{lock} {uname}",
                callback_data=GetUnitCallback(unit_id=uid).pack()
            )
            row.append(button)
        keyboard_buttons.append(row)

    # --- Pagination navigation buttons ---
    nav_buttons = []

    # Create a temporary PagesCallback for generating buttons, reflecting the *current* state of the view
    temp_prev_data_for_buttons = PagesCallback(
        start=current_start,
        end=current_end,
        pattern=prev_data.pattern,
        action=PagesAction.REFRESH # Action here reflects the current view for generating buttons
    )

    if temp_prev_data_for_buttons.start > 0:
        nav_buttons.append(back_page_button(temp_prev_data_for_buttons))
    else:
        nav_buttons.append(types.InlineKeyboardButton(text=" ", callback_data="no_op"))

    if temp_prev_data_for_buttons.end < total_items:
        nav_buttons.append(next_page_button(temp_prev_data_for_buttons, total_items))
    else:
        nav_buttons.append(types.InlineKeyboardButton(text=" ", callback_data="no_op"))

    keyboard_buttons.append(nav_buttons)
    keyboard_buttons.append([refresh_page_button(temp_prev_data_for_buttons)])

    return types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


# def pages_result(items: list, prev_data: PagesCallback):
#     keyboard_buttons = []
#     total_items = len(items)
#
#     # Determine the actual start and end for the current page being displayed.
#     # This logic is crucial to correctly handle initial loads, refreshes,
#     # and cases where the items list size changes.
#     current_start = prev_data.start
#     current_end = prev_data.end
#
#     # If the action was REFRESH, or if the current page data is invalid for the current `items`
#     # (e.g., `start` is beyond `total_items`, or `end` is less than `start` and there are items),
#     # reset to the first page.
#     if prev_data.action == PagesAction.REFRESH or \
#        current_start >= total_items or \
#        (current_end <= current_start and total_items > 0):
#         current_start = 0
#         current_end = min(ITEMS_PER_PAGE, total_items)
#     else:
#         # For NEXT/BACK actions, ensure bounds are respected
#         current_start = max(0, min(current_start, total_items))
#         current_end = min(current_start + ITEMS_PER_PAGE, total_items)
#
#
#     print(f"ITEMS LEN: {total_items}, Displaying from: {current_start} to {current_end}")
#
#     # Display items for the current page
#     # Ensure items[current_start:current_end] is valid
#     items_to_display = items[current_start:current_end]
#     if not items_to_display and total_items > 0:
#         # This can happen if, for example, we go to page 2 but page 2 is now empty due to data changes.
#         # In this case, try to go back to the previous valid page or the first page.
#         print("Adjusting page: current slice is empty, but items exist.")
#         current_start = max(0, total_items - ITEMS_PER_PAGE) # Go to the last possible full/partial page
#         current_end = total_items
#         items_to_display = items[current_start:current_end]
#         print(f"Adjusted to: {current_start} to {current_end}")
#
#
#     for batch in itertools.batched(items_to_display, 2):
#         row = []
#         for i in batch:
#             lock = i.get("_lock_", ObjState.UNKNOWN)
#             uid = i["id"]
#             uname = i["nm"]
#             button = types.InlineKeyboardButton(
#                 text=f"{lock} {uname}",
#                 callback_data=GetUnitCallback(unit_id=uid).pack()
#             )
#             row.append(button)
#         keyboard_buttons.append(row)
#
#     # --- Pagination navigation buttons ---
#     nav_buttons = []
#
#     # Create a temporary PagesCallback for generating buttons, reflecting the *current* state of the view
#     # This is important so the 'back' and 'next' buttons know what state to transition FROM.
#     temp_prev_data_for_buttons = PagesCallback(
#         start=current_start,
#         end=current_end,
#         pattern=prev_data.pattern, # Carry over the pattern
#         action=PagesAction.REFRESH # The action here doesn't really matter for button generation, but REFLECTS that we're showing the current page.
#                                    # The button functions themselves will set the action for the *next* callback.
#     )
#
#     # Only show "Back" button if not on the very first item
#     if temp_prev_data_for_buttons.start > 0:
#         nav_buttons.append(back_page_button(temp_prev_data_for_buttons))
#     else:
#         nav_buttons.append(types.InlineKeyboardButton(text=" ", callback_data="no_op")) # Placeholder
#
#     # Only show "Next" button if there are more items to display
#     if temp_prev_data_for_buttons.end < total_items:
#         nav_buttons.append(next_page_button(temp_prev_data_for_buttons, total_items))
#     else:
#         nav_buttons.append(types.InlineKeyboardButton(text=" ", callback_data="no_op")) # Placeholder
#
#     keyboard_buttons.append(nav_buttons)
#     keyboard_buttons.append([refresh_page_button(temp_prev_data_for_buttons)])
#
#     return types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


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
