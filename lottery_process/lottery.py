from db import connect_db, get_promo
from create_bot import bot
import random
import asyncio
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message


async def draw_lottery():
    print('draw')
    """Функция розыгрыша лотереи, разыгрывает до достижения total_play"""
    conn = connect_db()
    cursor = conn.cursor()

    # Выбираем лотереи, у которых remaining_tickets = 0
    # и нет записей в payments со статусом in_progress
    cursor.execute("""
        SELECT id, played, total_play 
        FROM promo 
        WHERE remaining_tickets = 0 
        AND id NOT IN (
            SELECT DISTINCT promo FROM payments WHERE status = 'in_progress'
        )
        AND NOT EXISTS (
            SELECT 1 FROM payments WHERE promo = promo.id AND status = 'in_progress'
        )
    """)
    tickets_ended_promos = cursor.fetchall()

    if not tickets_ended_promos:
        return  # Завершаем выполнение, если нет подходящих акций

    for promo_id, played, total_play in tickets_ended_promos:
        # Проверяем, есть ли назначенный победитель
        cursor.execute("""
            SELECT users.id, users.telegram_name, users.telegram_id 
            FROM predefined_winners 
            JOIN users ON users.id = predefined_winners.user_id 
            WHERE promo = ?
        """, (promo_id,))
        predefined_winner = cursor.fetchone()

        if predefined_winner:
            winner_id, winner_name, winner_telegram_id = predefined_winner
        else:
            # Получаем всех участников и их количество билетов
            cursor.execute("""
                SELECT users.id, users.telegram_name, tickets.quantity, users.telegram_id 
                FROM tickets 
                JOIN users ON users.id = tickets.owner 
                WHERE tickets.promo = ?
            """, (promo_id,))
            participants = cursor.fetchall()

            if not participants:
                continue  # Пропускаем, если участников нет

            # Считаем общее количество билетов
            total_tickets = sum(ticket[2] for ticket in participants)

            # Генерируем случайное число от 1 до общего количества билетов
            winning_ticket = random.randint(1, total_tickets)

            # Ищем победителя, накапливая билеты
            current_sum = 0
            for user_id, username, ticket_count, telegram_id in participants:
                current_sum += ticket_count
                if current_sum >= winning_ticket:
                    winner_id, winner_name, winner_telegram_id = user_id, username, telegram_id
                    break

        # Записываем победителя в winners
        cursor.execute("INSERT INTO winners (promo, user_id) VALUES (?, ?)", (promo_id, winner_id))
        # Увеличиваем `played` на 1
        cursor.execute("""
            UPDATE promo 
            SET played = played + 1, remaining_tickets = total_tickets
            WHERE id = ?
        """, (promo_id,))
        # Обнуляем количество билетов (quantity) у всех записей, где promo_id = promo
        cursor.execute("UPDATE tickets SET quantity = 0 WHERE promo = ?", (promo_id,))

        conn.commit()

        # Отправляем сообщение победителю

        await send_congratulation(winner_telegram_id, promo_id)

    conn.close()


async def cancel_unpaid_reservations():
    """Отменяет неоплаченные бронирования и возвращает билеты в продажу"""
    while True:
        # print('Обход')
        conn = connect_db()
        cursor = conn.cursor()

        # Получаем все резервации старше 10 минут
        cursor.execute(
            """SELECT users.telegram_id, users.id, payments.promo, payments.quantity, payments.pay_message_id 
               FROM payments
               JOIN users ON users.id = payments.user_id
               WHERE payments.created_at < strftime('%s', 'now', '-20 minutes')
               AND payments.status = 'in_progress'"""
        )
        expired_reservations = cursor.fetchall()
        # print(expired_reservations)

        for telegram_id, db_user_id, promo_id, quantity, message_id in expired_reservations:
            try:
                await bot.delete_message(chat_id=telegram_id, message_id=message_id)
                await bot.send_message(text="❌ Ваш платёж был отменён из-за истечения времени.", chat_id=telegram_id)

            except Exception as e:
                print(f"Ошибка при удалении инвойса: {e}")

            # Возвращаем билеты в продажу
            cursor.execute("UPDATE promo SET remaining_tickets = remaining_tickets + ? WHERE id = ?",
                           (quantity, promo_id))

            cursor.execute("UPDATE payments SET status = 'canceled' WHERE promo = ? AND user_id = ? AND "
                           "pay_message_id = ?",
                           (promo_id, db_user_id, message_id))

        conn.commit()
        conn.close()
        await asyncio.sleep(600)  # Проверяем каждые 10 минут


async def send_congratulation(user_id, promo_id):
    conn = connect_db()
    cursor = conn.cursor()

    # Получаем данные победителя
    cursor.execute("SELECT telegram_id, telegram_name, name, city, address, phone, email FROM users WHERE telegram_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        print("Ошибка: победитель не найден!")
        conn.close()
        return

    winner_telegram_id, username, name, city, address, phone, email = user_data

    # Получаем список админов
    cursor.execute("SELECT telegram_id FROM admins")
    admin_data = cursor.fetchall()
    admin_ids = {admin[0] for admin in admin_data}  # Множество ID админов

    # Получаем список всех пользователей, кроме админов
    cursor.execute("SELECT telegram_id FROM users WHERE telegram_id NOT IN (SELECT telegram_id FROM admins)")
    users_data = cursor.fetchall()
    user_ids = {user[0] for user in users_data}  # Множество всех пользователей (без админов)

    conn.close()

    # Формируем название акции
    promo_name = get_promo(promo_id)

    text_back = f'Для возвращения в розыгрыш или меню нажмите /start'
    # 📢 **Сообщение для всех пользователей (кроме админов)**
    public_text = f"🎉 В розыгрыше {promo_name} победитель - {name}!\n📍 Город: {city}\n\n"
    public_text_with_back = public_text + text_back

    winner_text = f'Поздравляем {name} Вы выиграли в розыгрыше {promo_name}\n\n'
    text_second = "Победитель обязуется разместить в чат https://t.me/festivalChat1 фото-видео отчет о получении приза в МВИДЕО, с указанием Имени и Города. Надеемся на понимание.\n\nЕсли Вам понравился наш розыгрыш постеров товаров, пригласите пожалуйста 3 друзей для участия в розыгрышах.\n\nСсылка приглашение — https://t.me/Festival24bot\n\n"
    text = winner_text + text_second + text_back

    # 🏆 **Сообщение победителю**
    await bot.send_message(
        chat_id=winner_telegram_id,
        text=f'🎊 {text}'
    )

    # 🎩 **Кнопка "Связаться" только для админов**
    user_link_button = None
    if username:
        user_url = f"https://t.me/{username}"
        user_link_button = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Связаться", url=user_url)]
        ])

    # 🔔 **Отправляем всем обычным пользователям (кроме победителя и админов)**
    for user_id in user_ids:
        if user_id != winner_telegram_id:
            try:
                await bot.send_message(chat_id=user_id, text=public_text_with_back)
            except:
                print(f"Ошибка отправки пользователю {user_id}")

    # 🛠 **Отправляем админам сообщение с контактами победителя**
    admin_text = f"🎉 В лотерее {promo_name} победил - {name}!\n📍 Город: {city}\n🏠 Адрес: {address}\n📞 Телефон: {phone}\n 📧 Email: {email}"
    for admin_id in admin_ids:
        await bot.send_message(
            chat_id=admin_id,
            text=admin_text,
            reply_markup=user_link_button if user_link_button else None
        )

    group_message = f"🎉 {name}, поздравляем с заслуженной победой!\n\nВаш новый {promo_name} уже ждёт вас в магазине МВИДЕО или СИТИЛИНК! ☕️\nДрузья, давайте вместе порадуемся за {name} — ждём видео с долгожданным призом! 📹✨\n\nХотите повторить успех? Всё просто!\n\n1️⃣ Переходите в бот: @Festival24bot\n2️⃣ Выбирайте постеры из нашего каталога\n3️⃣ Участвуйте в розыгрышах, покупайте постеры.\n\n🚀 Новые конкурсы стартуют совсем скоро — не пропустите свой шанс на победу!"
    await bot.send_message(chat_id=-1002283734085, text=group_message)

#
# async def send_govno_message(message: Message):
#     await bot.send_message(chat_id=571294067, text=f"chat_id: {message.chat.id}")
