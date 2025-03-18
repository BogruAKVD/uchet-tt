from aiogram.filters import Command
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext


from utils import get_start_keyboard

common_router = Router()




@common_router.message(Command("start"))
async def start_command(message: types.Message):
    keyboard = get_start_keyboard(message.from_user)
    await message.answer("Добро пожаловать!", reply_markup=keyboard)


@common_router.callback_query(F.data == "cancel")
async def cancel_all_operations(query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    keyboard=get_start_keyboard(query.from_user)
    await query.message.answer("Все операции отменены. Возвращаемся в начало.", reply_markup=keyboard)
