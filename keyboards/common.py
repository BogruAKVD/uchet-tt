from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def add_cancel_button(keyboard: InlineKeyboardMarkup = None):
    if keyboard is None:
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Завершить без сохранения", callback_data="cancel")]],
            resize_keyboard=True)
    else:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="Завершить без сохранения", callback_data="cancel")])
        return keyboard
