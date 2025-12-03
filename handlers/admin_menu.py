from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup


admin_main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Начать просмотр актульаных заявок")]
    ],
    resize_keyboard=True
)

admin_interactive_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Прекратить просмотр актуальных заявок")]
    ],
    resize_keyboard=True
)

user_choose_menu = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="100 рублей сейчас!", callback_data="prize:money"),
    InlineKeyboardButton(text="Розыгрыш 3000 рублей!", callback_data="prize:raffle")
]])