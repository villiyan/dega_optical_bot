import redis
import os
from aiogram.fsm.storage.redis import RedisStorage
from сonfig import REDIS_HOST, REDIS_PORT, REDIS_DB_STATES, REDIS_DB_DATA

# Формирование URL-строки для подключения к Redis
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Настройка хранилища состояний для db0
storage = RedisStorage.from_url(redis_url)

# Подключение к db2 для хранения фактических данных
data_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB_DATA, decode_responses=False)

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
