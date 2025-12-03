import html
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Твои импорты (убедись, что пути правильные)
from database import data_client
import handlers.universal_methods as uni
import handlers.admin_menu as mens

router = Router()


class ReviewState(StatesGroup):
    reviewing = State()


# --- КЛАВИАТУРА АДМИНА ---
def review_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="approve"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data="reject"),
        ],
        [
            InlineKeyboardButton(text="🛑 Остановить просмотр", callback_data="stop_review")
        ]
    ])


# --- ХЕНДЛЕР: НАЧАЛО ПРОСМОТРА ---
@router.message(F.text == "Начать просмотр актульаных заявок")
async def start_review(message: Message, state: FSMContext, bot: Bot):
    await message.answer(text="Начинаем просмотр заявок", reply_markup=mens.admin_interactive_menu)
    await state.set_state(ReviewState.reviewing)
    # Запускаем цикл показа фото
    await send_next_image(message.chat.id, state, bot)


# --- ФУНКЦИЯ: ОТПРАВКА СЛЕДУЮЩЕГО ФОТО ---
async def send_next_image(chat_id: int, state: FSMContext, bot: Bot):
    # Достаем заявку и сразу удаляем её из очереди (твой метод)
    result = uni.pop_oldest_and_delete(data_client)

    # Если заявок нет
    if not result:
        await bot.send_message(chat_id, "Нет новых заявок.", reply_markup=mens.admin_main_menu)
        await state.clear()
        return

    redis_key = result[0]  # ключ, например 'user:12345:image'
    all_data = result[1]  # словарь данных

    # --- 1. ПАРСИМ ДАННЫЕ ИЗ REDIS (Декодируем байты) ---

    # Приз
    prize_val = all_data.get('prize', 'Не указан')
    if isinstance(prize_val, bytes): prize_val = prize_val.decode('utf-8')

    # Имя пользователя
    full_name = all_data.get('full_name', 'Неизвестный')
    if isinstance(full_name, bytes): full_name = full_name.decode('utf-8')
    # Экранируем спецсимволы, чтобы не сломать HTML
    full_name = html.escape(full_name)

    # Юзернейм
    username = all_data.get('username', '')
    if isinstance(username, bytes): username = username.decode('utf-8')

    # Картинка (оставляем байтами)
    image_bytes = all_data['image']

    # ID пользователя из ключа
    user_id = redis_key.split(":")[1]

    # Проверка ID на адекватность
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        await bot.send_message(chat_id, f"Ошибка данных: user_id ({user_id}) битый.")
        # Пробуем следующее фото, чтобы не застрять
        await send_next_image(chat_id, state, bot)
        return

    # --- 2. ФОРМИРУЕМ КЛИКАБЕЛЬНУЮ ССЫЛКУ ---
    # Ссылка работает даже без юзернейма
    user_link = f'<a href="tg://user?id={user_id}">{full_name}</a>'

    # Добавляем юзернейм текстом, если он есть
    if username and username != "net_nika":
        user_display = f"{user_link} (@{username})"
    else:
        user_display = user_link

    # --- 3. СОХРАНЯЕМ В FSM (ЧТОБЫ КНОПКИ ЗНАЛИ, КОГО ОДОБРЯТЬ) ---
    await state.update_data(current_user_id=user_id, current_prize=prize_val)

    # --- 4. ОТПРАВЛЯЕМ АДМИНУ ---
    photo_file = BufferedInputFile(
        file=image_bytes,
        filename=f"user_{user_id}.jpg"
    )

    caption_text = (
        f"👤 <b>От кого:</b> {user_display}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"🎁 <b>Хочет получить:</b> {prize_val}"
    )

    await bot.send_photo(
        chat_id,
        photo=photo_file,
        caption=caption_text,
        parse_mode="HTML",  # Важно для работы ссылки
        reply_markup=review_keyboard()
    )


# --- ХЕНДЛЕР: ОБРАБОТКА КНОПОК ---
@router.callback_query(ReviewState.reviewing, F.data.in_(["approve", "reject", "stop_review"]))
async def process_review(callback: CallbackQuery, state: FSMContext, bot: Bot):
    # Достаем данные текущего юзера из памяти
    data = await state.get_data()
    current_user_id = data.get('current_user_id')
    current_prize = data.get('current_prize', 'Награда')

    # Логика кнопок
    if callback.data == "approve":
        # Уведомляем юзера
        if current_user_id:
            try:
                await bot.send_message(current_user_id, f"🎉 Ваша заявка ({current_prize}) одобрена! Ожидайте.")
            except Exception:
                pass  # Если бот в блоке, не падаем

        # Меняем сообщение у админа
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n✅ <b>ОДОБРЕНО</b>",
            parse_mode="HTML"
        )
        # Идем дальше
        await send_next_image(callback.message.chat.id, state, bot)

    elif callback.data == "reject":
        # Уведомляем юзера
        if current_user_id:
            try:
                await bot.send_message(current_user_id,
                                       "❌ Ваш отзыв не прошел проверку или фото нечитаемо. Попробуйте снова.")
            except Exception:
                pass

        # Меняем сообщение у админа
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n❌ <b>ОТКЛОНЕНО</b>",
            parse_mode="HTML"
        )
        # Идем дальше
        await send_next_image(callback.message.chat.id, state, bot)

    elif callback.data == "stop_review":
        await state.clear()
        await callback.message.delete()  # Удаляем последнее фото, чтобы не висело
        await callback.message.answer("🛑 Просмотр заявок остановлен.", reply_markup=mens.admin_main_menu)

    await callback.answer()


# --- ХЕНДЛЕР: ЕСЛИ АДМИН НАЖАЛ ТЕКСТОВУЮ КНОПКУ "ПРЕКРАТИТЬ" ---
@router.message(F.text == "Прекратить просмотр актуальных заявок")
async def stop_list_text(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Просмотр завершен.", reply_markup=mens.admin_main_menu)