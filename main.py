import asyncio
import os
import logging
from aiogram import Bot, Dispatcher
from aiohttp import web  # Нужен для Render
from сonfig import API_TOKEN
from database import storage, data_client  # save_data_to_disk убираем, на Render нет диска
from handlers import routers

# Настройка логов, чтобы видеть ошибки в консоли Render
logging.basicConfig(level=logging.INFO)

TOKEN = API_TOKEN
# Админов лучше хранить в .env, но пока пусть будет так
ADMINS = [507618077]

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)


# --- ФЕЙКОВЫЙ ВЕБ-СЕРВЕР ---
async def health_check(request):
    # Просто возвращаем "ОК", чтобы Render видел, что мы живы
    return web.Response(text="Bot is running OK")


async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)  # На всякий случай

    runner = web.AppRunner(app)
    await runner.setup()

    # Render сам выдаст порт через переменную окружения PORT
    port = int(os.environ.get("PORT", 8080))

    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Web server started on port {port}")


# ---------------------------

async def main():
    # Работа с админами в Redis
    try:
        # Проверяем коннект к редису
        await data_client.ping()
        logging.info("Redis connected successfully")

        if await data_client.exists('admins'):
            await data_client.delete('admins')

        for admin_id in ADMINS:
            await data_client.sadd('admins', admin_id)

        admins = await data_client.smembers('admins')
        logging.info(f"Admins in Redis: {admins}")

    except Exception as e:
        logging.error(f"Redis connection failed: {e}")

    # Подключаем роутеры
    for router in routers:
        dp.include_router(router)

    # Чистим вебхуки (важно при переходе на поллинг)
    await bot.delete_webhook(drop_pending_updates=True)

    # Запускаем ПАРАЛЛЕЛЬНО: Бот + Веб-сервер
    await asyncio.gather(
        dp.start_polling(bot),
        start_web_server()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")