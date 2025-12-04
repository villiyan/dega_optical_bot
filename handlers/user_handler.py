from aiogram import Router, F, Bot
from aiogram.types import Message, ContentType, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import data_client
from io import BytesIO
import time
import handlers.universal_methods as uni
from handlers.admin_menu import admin_main_menu, user_choose_menu

router = Router()

class ReviewState(StatesGroup):
    waiting_for_prize = State()

class Img_Send(StatesGroup):
    img = State()

@router.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    is_admin = await data_client.sismember('admins', user_id)
    if is_admin:
        await message.answer(f"Добрый день, {message.from_user.full_name}", reply_markup=admin_main_menu)
    else:
        await state.set_state(ReviewState.waiting_for_prize)
        await message.answer("""Добрый день! Спасибо за ваш заказ.
                                Мы работаем над повышением рейтинга магазина и будем признательны за вашу высокую оценку. За опубликованный отзыв (5 звезд) предусмотрено вознаграждение.
                                Как это работает?
                                Вы присылаете скриншот отзыва боту. Наш менеджер проверяет его наличие и соответствие правилам акции. После верификации вы сможете выбрать удобный формат бонуса:
                                -Моментальная выплата 100 рублей на мобильный телефон.
                                -Регистрация в розыгрыше 3000 рублей.
                                Пожалуйста, выберите желаемый вариант.""", reply_markup=user_choose_menu)


@router.callback_query(ReviewState.waiting_for_prize, F.data.startswith("prize:"))
async def begin_sending(call: CallbackQuery, state: FSMContext):
    choice_code = call.data.split(":")[1]

    if choice_code == "money":
        prize_text = "100 РУБЛЕЙ"
        msg_text = "Выбрано: 100 рублей на телефон."
    else:
        prize_text = "РОЗЫГРЫШ 3000"
        msg_text = "Выбрано: участие в розыгрыше 3000р."

    # !!! ГЛАВНОЕ ИЗМЕНЕНИЕ: Запоминаем выбор в памяти (FSM) !!!
    await state.update_data(selected_prize=prize_text)

    await state.set_state(Img_Send.img)

    # Редактируем сообщение, чтобы зафиксировать выбор и попросить фото
    await call.message.edit_text(f"{msg_text}\n\nТеперь, пожалуйста, отправьте скриншот вашего отзыва (как фото).")
    await call.answer()


@router.message(Img_Send.img, F.content_type == ContentType.PHOTO)
async def process_photo(message: Message, state: FSMContext, bot: Bot):
    try:
        # 1. Достаем то, что сохранили на прошлом шаге
        user_data = await state.get_data()
        prize_val = user_data.get("selected_prize", "Неизвестно")  # Дефолт на всякий случай

        # 2. Получение файла
        file_id = message.photo[-1].file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        file_bytes = BytesIO()
        await bot.download_file(file_path, destination=file_bytes)
        image_data = file_bytes.getvalue()
        user_id = message.from_user.id

        # 3. Сохранение в Redis (Теперь вместе с полем prize!)
        key = f"user:{user_id}:image"

        await uni.safe_hset(data_client, key, {
            "image": image_data,
            "is_checked": "0",
            "created_at": time.time(),
            "prize": prize_val  # <--- Вот оно! Теперь админ увидит выбор
        })

        # Уведомление админам
        admins = await data_client.smembers('admins')
        # Аккуратнее с декодированием, вдруг там пусто
        if admins:
            admins_list = [admin.decode() if isinstance(admin, bytes) else admin for admin in admins]
            for admin in admins_list:
                try:
                    await bot.send_message(admin, f"Пользователь {user_id} отправил заявку! Хочет: {prize_val}")
                except:
                    pass  # Если бота заблочил админ, не падаем

        await message.answer("Данные получены! Ожидайте подтверждения администратора.")

    except Exception as e:
        await message.answer("Произошла ошибка при обработке. Пожалуйста, нажмите /start и попробуйте снова.")
        print(f"Error in process_photo: {e}")

    finally:
        await state.clear()  # Очищаем память, выбор и фото забываются


@router.message(Img_Send.img)
async def invalid_photo(message: Message, state: FSMContext):
    await message.answer("Формат ответа не подтверждён! Пришлите скриншот как картинку.")
