import asyncio
from handlers.client import router as client_router
from handlers.client_profile import router as profile_router
from handlers.admin import router as admin_router
from create_bot import dp, bot
from db import connect_db
from lottery_process.lottery import draw_lottery, cancel_unpaid_reservations
from fastapi import FastAPI, Request
from uvicorn.config import Config
from uvicorn.server import Server
from payment import successful_payment_handler
from urllib.parse import parse_qs
import json
# Подключаем router
dp.include_router(client_router)
dp.include_router(profile_router)
dp.include_router(admin_router)


async def start_bot():
    await dp.start_polling(bot, skip_updates=True)
    await draw_lottery()


async def run_server():
    api_config = Config(app=app, host="127.0.0.1", port=2228, reload=True)
    server = Server(api_config)
    await server.serve()


async def main():
    await asyncio.gather(
        start_bot(),
        cancel_unpaid_reservations(),
        run_server()
    )


app = FastAPI()


@app.post("/payment")
async def read_any_path(request: Request):
    body = await request.body()  # Получаем тело запроса
    content_type = request.headers.get("content-type", "")

    order_num = None
    quantity = None
    status = None
    parsed_body = {}

    try:
        if "application/json" in content_type:
            # Если JSON → разбираем через json.loads()
            parsed_body = json.loads(body.decode("utf-8"))
            order_num = parsed_body.get("order_num")
            status = parsed_body.get("payment_status")

            # Исправленный парсинг количества товаров
            products = parsed_body.get("products", [])
            if isinstance(products, list) and products:
                quantity = products[0].get("quantity")

        elif "application/x-www-form-urlencoded" in content_type:
            # Если form-data → разбираем через parse_qs()
            parsed_body = parse_qs(body.decode("utf-8"))
            order_num = parsed_body.get("order_num", [None])[0]
            status = parsed_body.get("payment_status", [None])[0]

            # Исправленный парсинг количества товаров
            quantity_key = next((key for key in parsed_body if key.startswith("products[0][quantity]")), None)
            if quantity_key:
                quantity = parsed_body[quantity_key][0]  # Достаём значение

        else:
            parsed_body = body.decode("utf-8", errors="replace")

    except Exception as e:
        print(f"Ошибка при разборе body: {e}")
        return {"status": "error", "message": "fuck_off"}

    if status == "success":
        await successful_payment_handler(int(order_num), int(quantity))
        await draw_lottery()
        return {"status": "success", "order_id": order_num, "quantity": quantity}
    else:
        print()
        return {"status": "fail"}


if __name__ == '__main__':
    asyncio.run(main())
   

