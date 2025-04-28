from create_bot import bot
from db import connect_db, get_user_telegram_id
from aiogram.types import FSInputFile
from keyboard.clientKB import main_menu_kb
import urllib.parse
from datetime import datetime, timedelta, UTC
import time


def generate_payment_link(order_id, phone, price, quantity):
    # URL платежной формы
    linktoform = "https://festival.payform.ru/"

    # Генерируем `link_expired` (на 15 минут больше текущего времени, UTC)
    expiration_time = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M")
    print(expiration_time)
    # Данные для оплаты
    data_1 = {
        "order_id": str(order_id),  # Уникальный ID заказа (в виде строки)
        "customer_phone": str(phone),  # Телефон покупателя
        "products[0][name]": "Постер",  # Название товара
        "products[0][price]": str(price),  # Цена товара (строка)
        "products[0][quantity]": str(quantity),  # Количество товара (строка)
        "do": "pay",  # Отправляем покупателя сразу на оплату
        "urlNotification": "https://festival.payform.ru/payment",  # Webhook уведомлений
        "currency": "rub",  # Валюта
        "link_expired": expiration_time,  # Срок действия ссылки (+15 минут)
        "payment_method": "AC",  # Метод оплаты (AC - банковская карта)
        "discount_value": "0.00",  # Скидка (строка)
        "urlSuccess": "https://t.me/Festival24bot",
    }
    data_2 = {
        "order_id": str(order_id),  # Уникальный ID заказа (в виде строки)
        "customer_phone": str(phone),  # Телефон покупателя
        "products[0][name]": "Постер",  # Название товара
        "products[0][price]": str(price),  # Цена товара (строка)
        "products[0][quantity]": str(quantity),  # Количество товара (строка)
        "do": "pay",  # Отправляем покупателя сразу на оплату
        "urlNotification": "https://festival.payform.ru/payment",  # Webhook уведомлений
        "currency": "rub",  # Валюта
        "link_expired": expiration_time,  # Срок действия ссылки (+15 минут)
        "payment_method": "SBP",  # Метод оплаты (AC - банковская карта)
        "discount_value": "0.00",  # Скидка (строка)
        "urlSuccess": "https://t.me/Festival24bot",

    }
    if phone == '89646221488' or phone == 89646221488:
        data_1['discount_value'] = str(int(price)-1)
    # Кодируем параметры в GET-запрос
    query_string_1 = urllib.parse.urlencode(data_1, doseq=True)
    query_string_2 = urllib.parse.urlencode(data_2, doseq=True)

    # Формируем финальную ссылку
    payment_link_card = f"{linktoform}?{query_string_1}"
    payment_link_sbp = f"{linktoform}?{query_string_2}"

    return payment_link_card, payment_link_sbp

async def create_payment(promo_id, user_id, quantity, message_id, price, phone):
    conn = connect_db()
    cursor = conn.cursor()
    create_time = int(time.time())

    # Обновляем количество оставшихся билетов
    cursor.execute(
        "UPDATE promo SET remaining_tickets = remaining_tickets - ? WHERE id = ?",
        (quantity, promo_id)
    )
    conn.commit()

    # Вставляем новую запись в payments
    cursor.execute("""
        INSERT INTO payments (user_id, promo, quantity, status, created_at, pay_message_id, price)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, promo_id, quantity, 'in_progress', create_time, message_id, price))

    conn.commit()

    # Получаем ID только что вставленного платежа
    payment_id = cursor.lastrowid

    # Генерируем ссылку на оплату
    payment_link_card, payment_link_spb = generate_payment_link(payment_id, phone, price, quantity)

    conn.close()

    return payment_link_card, payment_link_spb


def check_payment_possible(user_id, promo_id, quantity):
    conn = connect_db()
    cursor = conn.cursor()

    # Проверяем, есть ли у пользователя неоплаченный инвойс
    cursor.execute("""
        SELECT pay_message_id FROM payments 
        WHERE user_id = ? AND status = 'in_progress' 
        LIMIT 1
    """, (user_id,))
    existing_payment = cursor.fetchone()

    if existing_payment:
        conn.close()
        return 1  # Уже есть неоплаченный платёж

    # Проверяем количество оставшихся билетов
    cursor.execute("SELECT remaining_tickets FROM promo WHERE id = ?", (promo_id,))
    promo_data = cursor.fetchone()

    remaining_tickets = promo_data[0]

    if remaining_tickets < quantity:
        conn.close()
        return 2  # Недостаточно билетов

    cursor.execute("SELECT name, city, address, phone, email FROM users WHERE id = ?", (user_id,))
    profile_data = cursor.fetchone()

    if profile_data is None:
        conn.close()
        return 3

    name, city, address, phone, email = profile_data

    if any(field is None for field in [name, city, phone, email]):
        conn.close()
        return 3  # Профиль не заполнен

    conn.close()

    return 0  # Всё ок, можно отправлять инвойс


def add_or_update_ticket(promo_id: int, user_id: int, quantity: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, quantity FROM tickets WHERE promo = ? AND owner = ?", (promo_id, user_id))

    ticket = cursor.fetchone()

    if ticket:
        ticket_id, current_quantity = ticket
        new_quantity = current_quantity + quantity
        cursor.execute("UPDATE tickets SET quantity = ? WHERE id = ?", (new_quantity, ticket_id))
    else:
        cursor.execute("INSERT INTO tickets (promo, owner, quantity) VALUES (?, ?, ?)", (promo_id, user_id, quantity))

    conn.commit()
    conn.close()


async def successful_payment_handler(order_num, quantity):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, promo, status FROM payments WHERE id = ?", (order_num,))
    payment_data = cursor.fetchone()
    user_id, promo_id, status = payment_data
    print(user_id, promo_id, status)
    user_telegram_id = get_user_telegram_id(user_id)
    print(user_telegram_id)
    try:
        if status != 'in_progress':
            raise 'Error finding payment'
        # Проверяем, существует ли категория и постер
        cursor.execute("SELECT category, img FROM promo WHERE id = ?", (promo_id,))
        promo_data = cursor.fetchone()

        category, poster = promo_data

        cursor.execute(
            "UPDATE payments SET status = 'accepted' WHERE id = ? AND status = 'in_progress'",
            (order_num, )
        )
        conn.commit()

        # ✅ Добавляем билеты в БД
        add_or_update_ticket(promo_id, user_id, quantity)

        # Отправляем постер как файл (если указан путь)
        if poster:
            try:
                poster_file = FSInputFile(poster)
                await bot.send_document(chat_id=user_telegram_id, document=poster_file, caption="🖼 Ваш постер!")
            except Exception as file_error:
                print(f"Ошибка при отправке постера: {file_error}")
                await bot.send_message(text="⚠ Не удалось отправить постер. Свяжитесь с поддержкой.", chat_id=user_telegram_id)

        await bot.send_message(text=
            f"✅ Оплата прошла успешно! Вы получили {quantity} постеров в розыгрыше '{category}'.",
            reply_markup=main_menu_kb, chat_id=user_telegram_id
        )

    except Exception as e:
        print(f"Ошибка при обработке платежа: {e}")
        await bot.send_message(text="❌ Ошибка при обработке платежа. Если деньги списались, свяжитесь с поддержкой.", chat_id=user_telegram_id)

    finally:
        conn.close()
