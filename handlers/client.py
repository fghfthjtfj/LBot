from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, PreCheckoutQuery, LabeledPrice
from aiogram.fsm.context import FSMContext
import sqlite3
from db import connect_db, user_cache, get_user, get_user_full_info
from keyboard.clientKB import *
from states import ClientStates
from aiogram.methods import SendInvoice
from config import PAYMENT_TOKEN
from aiogram.filters import StateFilter
from datetime import datetime
from payment import check_payment_possible, add_or_update_ticket, create_payment
import re
router = Router()
text = "Добро пожаловать! Вы в главном меню.\nПосмотрите наших счастливых победителей, нажав кнопку \"Наши Победители\".\nВозвращайтесь за Вашей Удачей!"


@router.message(F.text == "/start")
async def send_welcome(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else None
    text_first = "«Победитель обязуется разместить в чат https://t.me/festivalChat1\nфото-видео отчет о получении приза, с указанием Имени и Города\nи пригласить 7 друзей для участия в розыгрышах»\nВ случае нарушения правил к дальнейшим розыгрышам не допускается.\nНадеемся на понимание."

    # Проверяем кэш вместо запроса в БД
    if user_id not in user_cache:
        conn = connect_db()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (telegram_id, telegram_name) VALUES (?, ?)", (user_id, username))
            conn.commit()
        except sqlite3.IntegrityError:
            pass

        conn.close()
        user_cache.add(user_id)
        await message.answer(text_first, reply_markup=main_menu_kb)
    else:
        await message.answer(text, reply_markup=main_menu_kb)
    await state.set_state(ClientStates.main_menu)


@router.callback_query(F.data == "back_button", StateFilter(ClientStates))
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=main_menu_kb)

    await state.set_state(ClientStates.main_menu)

    await callback.answer()


@router.callback_query(F.data == "shop", ClientStates.promo_menu)
async def shop(callback: CallbackQuery, state: FSMContext):
    products_kb = await create_shop_kb()

    description = ("Выберите товар для покупки"
    )

    await callback.message.edit_text(
        description,
        reply_markup=products_kb
    )
    await state.set_state(ClientStates.shop_menu)

    await callback.answer()


def escape_markdown_v2(text: str) -> str:
    """Экранирует спецсимволы для MarkdownV2"""
    escape_chars = r"_*[]()~`>#+-=|{}.!<>"
    return re.sub(r"([{}])".format(re.escape(escape_chars)), r"\\\1", text)


@router.callback_query(F.data.startswith("product_id_"), ClientStates.shop_menu)
async def open_product(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()

    product_id = callback.data.split("_")[-1]

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, desc, price, img_path FROM products WHERE id = ?", (product_id,))
    category = cursor.fetchone()
    conn.close()

    p_id, desc, price, img_path = category
    desc = desc.encode('raw_unicode_escape').decode('unicode_escape')

    # ✅ Экранируем спецсимволы
    text = escape_markdown_v2(desc)

    photo = FSInputFile(img_path)

    product_kb = draw_product_buy(price, p_id)
    await state.update_data(product_price=price, p_id=p_id)
    await callback.message.answer_photo(
        photo,
        caption=text,  # Теперь Telegram не выдаст ошибку
        parse_mode="MarkdownV2",  # Используем MarkdownV2
        reply_markup=product_kb
    )

    await state.set_state(ClientStates.product_info)
    await callback.answer()


@router.callback_query(F.data.startswith("buy_product_"), ClientStates.product_info)
async def buy_product_menu(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    price = data['product_price']
    p_id = data['p_id']
    product_kb = draw_product_buy(price, p_id)
    if callback.message.caption != 'Нет в наличии':
        await callback.message.edit_caption(caption='Нет в наличии', reply_markup=product_kb)
    #await state.set_state(ClientStates.main_menu)


@router.callback_query(F.data == "lottery_info", ClientStates.main_menu)
async def lottery_info(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_text(
            "Здесь будет информация о новых постерах",
            reply_markup=main_menu_kb
        )
    except Exception as e:
        if "message is not modified" in str(e):
            await callback.answer()


@router.callback_query(F.data == "lottery_categories", ClientStates.main_menu)
async def lottery_categories(callback: CallbackQuery, state: FSMContext):
    categories_kb = await categories_kb_draw()
    # description = (
    #     "🖼️ Выберите постер и украсьте своё пространство! 🎨\n\n"
    #     "Каждый постер в этом списке – это не просто изображение, а уникальный цифровой файл, "
    #     "который можно скачать и использовать по своему желанию.\n\n"
    #     "🔹 Что входит в покупку?\n"
    #     "✔️ Оригинальный постер в высоком разрешении (доступен для скачивания)\n"
    #     "✔️ Моментальная доставка файла – получите изображение сразу после покупки\n"
    #     "✔️ Высокое качество печати – подходит для оформления интерьера, подарка или личной коллекции\n\n"
    #     "🏡 Украсьте дом или рабочее место стильным постером!\n"
    #     "Выберите понравившийся дизайн и скачайте файл в один клик. 🚀"
    # )
    description = "Выберите постер и участвуйте в розыгрыше призов\n\n" \
       "Каждый постер в этом списке - не просто изображение, а Ваш билет в розыгрыш.\n" \
       "Покупая постер с изображением приза, вы получаете цифровой файл и одновременно шанс выиграть приз.\n" \
       "Выберите понравившийся постер и сделайте первый шаг к выигрышу.\n" \
       "Количество постеров и шансов выиграть не ограничено.\n" \
       "Нажимайте /start и заходите снова в программу.\n" \
       "Постеры суммируются на Ваш номер телефона."


    await callback.message.edit_text(
        description,
        reply_markup=categories_kb
    )

    # Устанавливаем состояние promo_menu
    await state.set_state(ClientStates.promo_menu)

    await callback.answer()




@router.callback_query(F.data.startswith("ticket_category_"), ClientStates.promo_menu)
async def open_ticket_category(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()

    category_id = callback.data.split("_")[-1]

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT category, start, end, img, desc FROM promo WHERE id = ?", (category_id,))
    category = cursor.fetchone()
    conn.close()

    name, start_unix, end_unix, img_path, desc = category
    start = datetime.fromtimestamp(start_unix).strftime("%d.%m.%Y")
    end = datetime.fromtimestamp(end_unix).strftime("%d.%m.%Y")

    text = (f"🎟 Категория: {name}\n"
            # f"📅 Начало: {start}\n⏳ Окончание: {end}\n "
            f"Выберите число постеров или укажите своё:")

    photo = FSInputFile(img_path)

    ticket_kb = await tickets_kb_draw(category_id)
    await callback.message.answer_photo(photo, caption=text, reply_markup=ticket_kb)

    await state.set_state(ClientStates.promo_info)
    await state.update_data(promo_id=category_id)

    await callback.answer()


@router.callback_query(TicketCallback.filter(), ClientStates.promo_info)
async def send_invoice_callback(callback: CallbackQuery, callback_data: TicketCallback, state: FSMContext):
    data = await state.get_data()

    promo_id = data.get("promo_id")
    quantity = callback_data.quantity
    price = callback_data.price
    total_price = int(price/quantity)  # Telegram требует цену в копейках

    user_data = get_user_full_info(callback.from_user.id)
    user_id = user_data[0]  # Получаем ID пользователя в БД
    username = user_data[2]
    phone = user_data[7]
    conn = connect_db()
    cursor = conn.cursor()

    # Получаем данные акции
    cursor.execute("SELECT category, remaining_tickets, poster FROM promo WHERE id = ?", (promo_id,))
    promo_data = cursor.fetchone()

    category, remaining_tickets, poster_path = promo_data

    check_result = check_payment_possible(user_id, promo_id, quantity)
    if not username:
        new_username = callback.from_user.username  # Берём username из callback, если он есть
        if new_username:
            cursor.execute("UPDATE users SET telegram_name = ? WHERE id = ?", (new_username, user_id))
            conn.commit()  # Не забудь commit()
            conn.close()
        else:
            await callback.message.answer("⚠ У вас отсутствует username в телеграм", reply_markup=back_kb)
            conn.close()
            return  # Выходим из функции, чтобы избежать ошибок

    # Проверяем, есть ли у пользователя неоплаченный инвойс
    if check_result == 1:
        await callback.message.answer("⚠ У вас уже есть неоплаченная заявка! Оплатите её или отмените.",
                                      reply_markup=cancel_payment_kb)
        await callback.answer()
        return
    if check_result == 2:
        await callback.message.answer(f"⚠ Осталось {remaining_tickets} постера! Укажите другое количество.")
        await callback.answer()
        return

    if check_result == 3:
        await callback.message.answer("⚠ Ваш профиль не заполнен полностью! Заполнить?", reply_markup=single_profile_kb)
        await state.set_state(ClientStates.main_menu)
        await callback.answer()
        return
    # Отправляем изображение перед инвойсом
    if poster_path:
        try:
            poster_file = FSInputFile(poster_path)  # Используем FSInputFile
            await callback.message.answer_photo(poster_file, caption="🖼 При покупке данного товара Вы получаете 1 "
                                                                     "постер.\nПостер "
                                                                     "'Пейте чай' - Плакат  идеальное решение для "
                                                                     "украшения интерьера вашего дома или любого "
                                                                     "другого места. Это цифровой продукт, "
                                                                     "который можно легко распечатать и получить "
                                                                     "качественное изображение. Плакаты — это "
                                                                     "стильные и эстетичные конструкции, "
                                                                     "которые добавят уникальности и индивидуальности "
                                                                     "вашему пространству. Сделайте свой дом или "
                                                                     "любое другое место более привлекательным с "
                                                                     "помощью этих красивых плакатов.")
        except Exception as file_error:
            print(f"Ошибка при отправке изображения: {file_error}")
            await callback.message.answer("⚠ Не удалось загрузить изображение.")



    # Отправляем сообщение с кнопкой
    invoice_message = await callback.message.answer("⬆️ Выберите удобный формат оплаты ⬆️ \nПосле успешной оплаты информация придет в этот чат-бот в течении 5-10 минут ❤️")
    pay_url_card, pay_url_sbp = await create_payment(promo_id, user_id, quantity, invoice_message.message_id, total_price, phone)
    link_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить картой", url=pay_url_card), InlineKeyboardButton(text="💳 Оплатить СБП", url=pay_url_sbp)], [cancel_payment_button]
    ])
    await invoice_message.edit_reply_markup(reply_markup=link_button)
    await state.set_state(ClientStates.main_menu)
    await callback.answer()


@router.message(ClientStates.promo_info, F.text.isdigit())
async def send_invoice_message(message: Message, state: FSMContext):
    """Обрабатывает ввод количества билетов через сообщение и отправляет инвойс"""

    data = await state.get_data()
    promo_id = data.get("promo_id")
    quantity = int(message.text)

    user_data = get_user_full_info(message.from_user.id)
    user_id = user_data[0]  # ID пользователя в БД
    username = user_data[2]
    phone = user_data[7]

    conn = connect_db()
    cursor = conn.cursor()

    # Получаем данные акции
    cursor.execute("SELECT category, remaining_tickets, ticket_price, poster FROM promo WHERE id = ?", (promo_id,))
    promo_data = cursor.fetchone()

    if not promo_data:
        await message.answer("❌ Ошибка: акция не найдена.")
        conn.close()
        return

    category, remaining_tickets, ticket_price, poster_path = promo_data

    total_price = quantity * ticket_price  # Telegram требует цену в копейках

    # Проверяем username пользователя
    if not username:
        new_username = message.from_user.username  # Берём username из message, если он есть
        if new_username:
            cursor.execute("UPDATE users SET telegram_name = ? WHERE id = ?", (new_username, user_id))
            conn.commit()
        else:
            await message.answer("⚠ У вас отсутствует username в Telegram", reply_markup=back_kb)
            conn.close()
            return

    # Проверяем возможность платежа
    check_result = check_payment_possible(user_id, promo_id, quantity)
    if check_result == 1:
        await message.answer("⚠ У вас уже есть неоплаченная заявка! Оплатите её или отмените.",
                             reply_markup=cancel_payment_kb)
        conn.close()
        return
    if check_result == 2:
        await message.answer(f"⚠ Осталось {remaining_tickets} постеров! Укажите другое количество.")
        conn.close()
        return
    if check_result == 3:
        await message.answer("⚠ Ваш профиль не заполнен полностью! Заполнить?", reply_markup=single_profile_kb)
        await state.set_state(ClientStates.main_menu)

        conn.close()
        return

    # Отправляем изображение перед инвойсом
    if poster_path:
        try:
            poster_file = FSInputFile(poster_path)
            await message.answer_photo(
                poster_file,
                caption="🖼 При покупке данного товара Вы получаете 1 постер.\n\n"
                        "📌 Постер — это стильное и эстетичное решение для украшения интерьера. "
                        "Цифровой продукт, который можно легко распечатать и украсить ваше пространство."
            )
        except Exception as file_error:
            print(f"Ошибка при отправке изображения: {file_error}")
            await message.answer("⚠ Не удалось загрузить изображение.")

    # Отправляем сообщение с кнопкой для оплаты
    invoice_message = await message.answer("Нажмите кнопку для оплаты:")
    pay_url_card, pay_url_sbp = await create_payment(promo_id, user_id, quantity, invoice_message.message_id, ticket_price, phone)

    link_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить картой", url=pay_url_card), InlineKeyboardButton(text="💳 Оплатить СБП", url=pay_url_sbp)], [cancel_payment_button]
    ])
    await invoice_message.edit_reply_markup(reply_markup=link_button)

    conn.close()
    await state.set_state(ClientStates.main_menu)


@router.callback_query(F.data == "cancel_payment")
async def cancel_payment_handler(callback: CallbackQuery, state: FSMContext):
    user_id = get_user(callback.from_user.id)

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE payments 
        SET status = 'canceled' 
        WHERE user_id = ? AND status = 'in_progress'
        RETURNING quantity, promo
    """, (user_id,))
    payment_data = cursor.fetchone()

    if not payment_data:
        await callback.answer("❌ Ошибка: платеж уже отменен или завершен.")
        conn.close()
        return
    quantity, promo_id = payment_data  # Достаём данные

    cursor.execute("""
            UPDATE payments SET status = 'canceled' 
            WHERE user_id = ?
        """, (user_id,))
    # Возвращаем билеты в продажу
    cursor.execute("UPDATE promo SET remaining_tickets = remaining_tickets + ? WHERE id = ?",
                   (quantity, promo_id))
    conn.commit()
    conn.close()
    await callback.message.edit_text("✅ Ваш платёж был отменён.", reply_markup=main_menu_kb)
    await state.set_state(ClientStates.main_menu)
    await callback.answer()
