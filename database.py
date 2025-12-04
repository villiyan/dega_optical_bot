import os
from redis.asyncio import Redis # Используем асинхронный клиент!
from aiogram.fsm.storage.redis import RedisStorage

# 1. Берем ссылку из настроек Render (или локалхост как запасной вариант)
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# 2. Создаем data_client ПРАВИЛЬНО (через from_url)
# Мы передаем туда redis_url, в котором уже зашит пароль и адрес
data_client = Redis.from_url(
    redis_url,
    decode_responses=False # Обязательно False, так как мы храним картинки (байты)
)

# 3. Если тебе нужен storage для состояний в том же редисе:
storage = RedisStorage.from_url(redis_url)

# Настройка сохранения данных на диск
def save_data_to_disk():
    data_client.save()

# Функции для работы с данными пользователей
def set_user_data(user_id, data):
    data_client.hset(f'user:{user_id}', mapping=data)

def get_user_data(user_id):
    return data_client.hgetall(f'user:{user_id}')

# Функции для работы с изображениями
def set_user_image(user_id, image_data):
    data_client.set(f'user:{user_id}:image', image_data)
    metadata = {'is_checked': 'False'}  # Преобразуем булевое значение в строку
    if metadata:  # Проверка, что словарь не пустой
        data_client.hset(f'user:{user_id}:image:metadata', mapping=metadata)
    else:
        print(f"Warning: Attempted to set empty metadata for user {user_id}")

def get_user_image(user_id):
    return data_client.get(f'user:{user_id}:image')

# Функция для удаления изображения
def delete_user_image(user_id):
    data_client.delete(f'user:{user_id}:image')
    data_client.delete(f'user:{user_id}:image:metadata')
