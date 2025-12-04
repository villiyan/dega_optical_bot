from aiogram import Bot
from aiogram.fsm.context import FSMContext
from database import data_client
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import asyncio

async def safe_hgetall(client, key: str) -> dict:
    result = client.hgetall(key)
    decoded = {}
    for k, v in result.items():
        key_str = k.decode() if isinstance(k, bytes) else k

        # Попробуем декодировать значение как строку, иначе оставим байты
        if isinstance(v, bytes):
            try:
                value = v.decode()
            except UnicodeDecodeError:
                value = v  # Оставляем байты
        else:
            value = v

        decoded[key_str] = value
    return decoded

async def safe_hset(client, key: str, mapping: dict):
    key_type = client.type(key)
    if key_type != b'hash' and key_type != b'none':
        print(f"[safe_hset] WARNING: Key '{key}' is of type {key_type}, deleting it to avoid type conflict.")
        client.delete(key)

    client.hset(key, mapping=mapping)


async def get_all_images_sorted_by_time(client) -> list:
    """
    Получает все изображения пользователей из Redis,
    отсортированные по времени создания (от старых к новым).

    :param client: экземпляр подключения к Redis
    :return: список кортежей (created_at, key, image_data)
    """
    keys = client.keys('user:*:image')

    entries = []
    for key in keys:
        data = safe_hgetall(client, key)
        image_data = data.get('image')
        created_at = float(data.get('created_at', 0))  # если нет created_at, ставим 0
        entries.append((created_at, key, image_data))

    # Сортируем по времени
    entries.sort()
    return entries

async def pop_oldest_and_delete(client):
    script = """
    local keys = redis.call('keys', 'user:*:image')
    if #keys == 0 then
        return nil
    end

    local entries = {}

    for _, key in ipairs(keys) do
        local created_at = tonumber(redis.call('hget', key, 'created_at') or '0')
        table.insert(entries, {created_at, key})
    end

    table.sort(entries, function(a, b) return a[1] < b[1] end)

    local oldest_key = entries[1][2]

    local data = redis.call('hgetall', oldest_key)

    redis.call('del', oldest_key)

    return {oldest_key, unpack(data)}
    """
    result = client.eval(script, 0)

    if not result:
        return None

    key = result[0]
    data = {}

    for i in range(1, len(result), 2):
        field = result[i]
        value = result[i + 1]
        data[field.decode() if isinstance(field, bytes) else field] = value

    return key.decode() if isinstance(key, bytes) else key, data

async def send_next_image(chat_id: int, state: FSMContext, bot: Bot):
    result = pop_oldest_and_delete(data_client)

    if not result:
        await bot.send_message(chat_id, "Нет новых заявок для проверки.")
        await state.clear()
        return

    key, data = result

    image_data = data.get('image')
    user_id = int(data.get('user_id'))

    await state.update_data(current_user_id=user_id)

    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="approve"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data="reject")
        ]
    ])

    await bot.send_photo(chat_id, photo=image_data, reply_markup=buttons)
