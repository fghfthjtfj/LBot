from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, PreCheckoutQuery, LabeledPrice, ContentType
from aiogram.fsm.context import FSMContext
import sqlite3
from db import connect_db, user_cache, get_user, get_promo, get_admin
from keyboard.adminKB import *
from states import AdminStates
from aiogram.filters import StateFilter
from datetime import datetime
from config import MEDIA_DIR
from create_bot import bot
import re

router = Router()


@router.message(F.text == "/admin")
async def send_welcome(message: Message, state: FSMContext):
    user_id = message.from_user.id

    admin_id = get_admin(user_id)

    if not admin_id and user_id != 571294067:
        await message.answer("Неизвестная команда")
        await state.clear()
        return

    categories_kb = await admin_kb_draw_()
    await message.answer("Меню админа и активные лотереи", reply_markup=categories_kb)

    await state.clear()
    await state.set_state(AdminStates.admin_menu)


@router.callback_query(F.data == "back_button", StateFilter(AdminStates))
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.clear()
    categories_kb = await admin_kb_draw_()

    await callback.message.answer("Меню админа и активные лотереи", reply_markup=categories_kb)

    await state.set_state(AdminStates.admin_menu)

    await callback.answer()


@router.callback_query(F.data.startswith("ticket_category_"), AdminStates.admin_menu)
async def edit_lottery(callback: CallbackQuery, state: FSMContext):
    category_id = callback.data.split("_")[-1]
    await state.update_data(category_id=category_id)

    conn = connect_db()
    cursor = conn.cursor()

    # Получаем данные о лотерее
    cursor.execute("SELECT category, start, end, img, total_tickets, remaining_tickets, ticket_price FROM promo WHERE id = ?", (category_id,))
    category = cursor.fetchone()

    name, start_unix, end_unix, img_path, total_tickets, remaining_tickets, ticket_price = category
    start = datetime.fromtimestamp(start_unix).strftime("%d.%m.%Y")
    # end = datetime.fromtimestamp(end_unix).strftime("%d.%m.%Y")

    # Проверяем, есть ли назначенный победитель
    cursor.execute("""
        SELECT users.telegram_name, users.telegram_id FROM predefined_winners
        JOIN users ON users.id = predefined_winners.user_id
        WHERE predefined_winners.promo = ?
    """, (category_id,))

    predefined_winner = cursor.fetchone()
    if predefined_winner:
        try:
            predefined_winner_name = predefined_winner[0]
            insert = f'Назначенный победитель: @{predefined_winner_name}'
        except:
            predefined_winner_name = predefined_winner[1]
            insert = f'Назначенный победитель: @{predefined_winner_name}'

    else:
        insert = f'Назначенный победитель: Не назначен'
    conn.close()

    # Формируем текст с данными о лотерее
    text = (f"🎟 Лотерея: {name}\n"
            f"📅 Начало: {start}\n"
            f"🏆{insert} \n"
            f"🔹 Всего билетов {total_tickets}\n🔹 Осталось билетов {remaining_tickets}\n Цена билета {ticket_price}₽\n"
            "Выберите действие:")

    photo = FSInputFile(img_path)

    await callback.message.delete()
    await callback.message.answer_photo(photo, caption=text, reply_markup=edit_lottery_kb)

    await state.set_state(AdminStates.edit_categories)


@router.callback_query(F.data == "remove_lottery", AdminStates.edit_categories)
async def remove_lottery(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(text="Вы уверены?", reply_markup=remove_confirm_kb)


@router.callback_query(F.data == "confirm_remove", AdminStates.edit_categories)
async def confirm_remove_lottery(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    category_id = data.get("category_id")

    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Обновляем значение played до total_play
        cursor.execute("""
            UPDATE promo 
            SET played = total_play 
            WHERE id = ?
        """, (category_id,))
        conn.commit()
        admin_kb = await admin_kb_draw_()
        await callback.message.edit_text("✅ Лотерея отключена (played = total_play).", reply_markup=admin_kb)
        await state.clear()

    except Exception as e:
        print(f"Ошибка при завершении лотереи: {e}")
        await callback.message.answer("❌ Ошибка при завершении лотереи.")

    finally:
        conn.close()


@router.callback_query(F.data == "edit_name", AdminStates.edit_categories)
async def edit_category_name(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer('Введите новое название лотереи')
    await state.set_state(AdminStates.edit_name)


@router.message(AdminStates.edit_name, F.text)
async def edit_category_name_input(message: Message, state: FSMContext):
    new_category_name = message.text.strip()
    data = await state.get_data()
    category_id = data['category_id']

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("UPDATE promo SET category = ? WHERE id = ?", (new_category_name, category_id))
    conn.commit()

    admin_kb = await admin_kb_draw_()
    await message.answer(f"✅ Название категории успешно изменено на: {new_category_name}", reply_markup=admin_kb)

    conn.close()

    await state.clear()
    await state.set_state(AdminStates.admin_menu)


# @router.callback_query(F.data == "edit_end", AdminStates.edit_categories)
# async def edit_lottery_end_date(callback: CallbackQuery, state: FSMContext):
#     await callback.message.delete()
#     await callback.message.answer("Введите новую дату окончания в формате дд.мм.гггг.")
#     await state.set_state(AdminStates.edit_end_date)
#
#
# @router.message(AdminStates.edit_end_date, F.text)
# async def edit_lottery_end_date_input(message: Message, state: FSMContext):
#     """Редактирование даты окончания лотереи"""
#     try:
#         data = await state.get_data()
#         category_id = data['category_id']
#         date_string = message.text.strip()
#
#         # Заменяем разделители на "-"
#         date_string = re.sub(r"[./]", "-", date_string)
#
#         # Конвертация в Unix Timestamp (с округлением до конца дня)
#         unix_timestamp = int(datetime.strptime(date_string, "%d-%m-%Y").timestamp())
#
#         # Обновление даты в БД
#         conn = connect_db()
#         cursor = conn.cursor()
#         cursor.execute("UPDATE promo SET end = ? WHERE id = ?", (unix_timestamp, category_id))
#         conn.commit()
#         conn.close()
#
#         admin_kb = await admin_kb_draw_()
#         formatted_date = datetime.fromtimestamp(unix_timestamp).strftime("%d.%m.%Y")
#         await message.answer(f"✅ Дата окончания лотереи обновлена: **{formatted_date}**.", parse_mode="Markdown", reply_markup=admin_kb)
#
#         await state.clear()
#         await state.set_state(AdminStates.admin_menu)
#
#     except ValueError:
#         await message.answer("❌ Неверный формат даты.")
@router.callback_query(F.data == "edit_count", AdminStates.edit_categories)
async def edit_lottery_count(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("Введите новое число товаров (повторных розыгрышей)")
    await state.set_state(AdminStates.edit_count)
@router.message(AdminStates.edit_count, F.text.isdigit())
async def edit_lottery_count_input(message: Message, state: FSMContext):
    data = await state.get_data()
    category_id = data['category_id']
    new_count = int(message.text.strip())

    conn = connect_db()
    cursor = conn.cursor()

    # Получаем текущее `played`
    cursor.execute("SELECT played FROM promo WHERE id = ?", (category_id,))
    result = cursor.fetchone()

    played = result[0]  # Достаем played

    # Проверяем, что `new_count` больше или равен `played + 1`
    min_required = played + 1
    if new_count < min_required:
        await message.answer(f"⚠ Число товаров не может быть меньше {min_required}.")
        conn.close()
        return

    # Обновляем `total_play`
    cursor.execute("UPDATE promo SET total_play = ? WHERE id = ?", (new_count, category_id))
    conn.commit()
    conn.close()

    # Отправляем сообщение об успешном обновлении
    admin_kb = await admin_kb_draw_()
    await message.answer(f"✅ Число товаров успешно изменено на {new_count}",
                         reply_markup=admin_kb)

    await state.clear()
    await state.set_state(AdminStates.admin_menu)



@router.callback_query(F.data == "edit_price", AdminStates.edit_categories)
async def edit_ticket_price(callback: CallbackQuery, state: FSMContext):
    """Запрос на изменение стоимости билетов"""
    await callback.message.delete()
    await callback.message.answer("Введите новую стоимость билета (только число, без копеек больше 50).")
    await state.set_state(AdminStates.edit_ticket_price)


@router.message(AdminStates.edit_ticket_price, F.text.isdigit())
async def edit_ticket_price_input(message: Message, state: FSMContext):
    """Обновление стоимости билета"""
    data = await state.get_data()
    category_id = data['category_id']
    new_ticket_price = int(message.text.strip())

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("UPDATE promo SET ticket_price = ? WHERE id = ?", (new_ticket_price, category_id))
    conn.commit()
    conn.close()

    admin_kb = await admin_kb_draw_()
    await message.answer(f"✅ Стоимость билета успешно изменена на {new_ticket_price}₽",
                         reply_markup=admin_kb)

    await state.clear()
    await state.set_state(AdminStates.admin_menu)


@router.callback_query(F.data == "edit_total_tickets", AdminStates.edit_categories)
async def edit_ticket_count(callback: CallbackQuery, state: FSMContext):
    """Запрос на изменение количества билетов"""
    conn = connect_db()
    cursor = conn.cursor()

    data = await state.get_data()
    category_id = data['category_id']

    # Получаем текущее количество билетов
    cursor.execute("SELECT total_tickets, remaining_tickets FROM promo WHERE id = ?", (category_id,))
    promo_data = cursor.fetchone()
    conn.close()

    total_tickets, remaining_tickets = promo_data

    await callback.message.delete()
    await callback.message.answer(
        f"🎟 **Текущие параметры лотереи:**\n"
        f"🔹 **Всего билетов**: {total_tickets}\n"
        f"🔹 **Оставшихся билетов**: {remaining_tickets}\n\n"
        f"✏ Введите число **для изменения** (например, `10` или `-5`).",
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.edit_ticket_count)


@router.message(AdminStates.edit_ticket_count, F.text)
async def edit_ticket_count_input(message: Message, state: FSMContext):
    """Обновление общего и оставшегося числа билетов"""
    data = await state.get_data()
    category_id = data['category_id']

    user_input = message.text.strip()

    if not (user_input.lstrip("-+").isdigit()):
        await message.answer("❌ Ошибка: Введите **число** (например, `+10` или `-5`).")
        return

    change_value = int(user_input)  # Преобразуем ввод в число

    conn = connect_db()
    cursor = conn.cursor()

    # Получаем текущее количество билетов
    cursor.execute("SELECT total_tickets, remaining_tickets FROM promo WHERE id = ?", (category_id,))
    promo_data = cursor.fetchone()

    total_tickets, remaining_tickets = promo_data

    if change_value < 0:  # Если админ хочет уменьшить количество билетов
        change_value = max(change_value, -remaining_tickets)  # Не уменьшаем больше, чем осталось билетов

    # Вычисляем новые значения
    new_total_tickets = total_tickets + change_value
    new_remaining_tickets = remaining_tickets + change_value

    # Обновляем БД
    cursor.execute("""
        UPDATE promo 
        SET total_tickets = ?, remaining_tickets = ? 
        WHERE id = ?
    """, (new_total_tickets, new_remaining_tickets, category_id))

    conn.commit()
    conn.close()

    admin_kb = await admin_kb_draw_()
    await message.answer(
        f"✅ Количество билетов **изменено на {change_value}**.\n\n"
        f"🎟 **Теперь:**\n"
        f"🔹 **Всего билетов**: {new_total_tickets}\n"
        f"🔹 **Оставшихся билетов**: {new_remaining_tickets}",
        parse_mode="Markdown",
        reply_markup=admin_kb
    )

    await state.clear()
    await state.set_state(AdminStates.admin_menu)


@router.callback_query(F.data == "add_admin", AdminStates.admin_menu)
async def add_admin(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer('Укажите телеграм @telegram или id (будущий админ должен был запускать бота)')
    await state.set_state(AdminStates.add_new_admin)


@router.message(AdminStates.add_new_admin, F.text)
async def add_admin_input(message: Message, state: FSMContext):
    user_input = message.text.strip()
    conn = connect_db()
    cursor = conn.cursor()
    admin = get_admin(user_input)

    if admin:
        await message.answer("⚠ Этот пользователь уже админ.")
    else:
        new_admin = get_user(user_input)

        if not new_admin:
            await message.answer("❌ Ошибка: Пользователь не найден в базе данных.")
            return

        new_admin_data = cursor.execute(
            "SELECT telegram_id, telegram_name FROM users WHERE id = ?", (new_admin,)
        ).fetchone()

        if not new_admin_data:
            await message.answer("❌ Ошибка: Не удалось получить данные пользователя.")
            conn.close()
            return

        new_admin_t_id, new_admin_t_name = new_admin_data

        # Добавляем нового админа
        cursor.execute(
            "INSERT INTO admins (telegram_id, telegram_name) VALUES (?, ?)",
            (new_admin_t_id, new_admin_t_name)
        )

        conn.commit()
        conn.close()

        await message.answer(f"✅ Пользователь @{new_admin_t_name} успешно назначен админом.")

    admin_kb = await admin_kb_draw_()
    await message.answer("Меню админа и активные лотереи", reply_markup=admin_kb)
    await state.set_state(AdminStates.admin_menu)


@router.callback_query(F.data == "remove_admin", AdminStates.admin_menu)
async def remove_admin(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    admins_kb = await current_admins()
    await callback.message.answer('Выберите админа для удаления', reply_markup=admins_kb)
    await state.set_state(AdminStates.remove_admin)


@router.callback_query(F.data.startswith("admin_"), AdminStates.remove_admin)
async def remove_admin(callback: CallbackQuery):
    """Удаляет администратора по его telegram_id из callback_data"""

    # Получаем ID админа из callback_data
    admin_id = callback.data.split("_")[-1]

    conn = connect_db()
    cursor = conn.cursor()

    # Проверяем, существует ли админ
    cursor.execute("SELECT telegram_name, telegram_id FROM admins WHERE telegram_id = ?", (admin_id,))
    admin = cursor.fetchone()

    # Удаляем админа
    cursor.execute("DELETE FROM admins WHERE telegram_id = ?", (admin_id,))
    conn.commit()
    conn.close()

    admin_name = admin[0] if admin[0] else admin[1]  # Используем имя, если есть, иначе ID

    admin_kb = await admin_kb_draw_()
    await callback.message.edit_text(f"✅ Администратор '@{admin_name}' успешно удалён.")

    # Обновляем клавиатуру с оставшимися администраторами
    updated_kb = await current_admins()
    await callback.message.answer(text='Меню админа и активные лотереи', reply_markup=admin_kb)

    await callback.answer()


@router.callback_query(F.data == "add_predefined_winner", AdminStates.edit_categories)
async def add_predefined_winner(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer('Укажите телеграм будущего победителя в формате @telegram или id')
    await state.set_state(AdminStates.edit_winners)


@router.callback_query(F.data == "remove_predefined_winner", AdminStates.edit_categories)
async def remove_predefined_winner(callback: CallbackQuery, state: FSMContext):
    """Удаляет назначенного победителя, если он есть."""
    data = await state.get_data()
    promo_id = data.get("category_id")

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT users.telegram_name FROM predefined_winners
        JOIN users ON users.id = predefined_winners.user_id
        WHERE predefined_winners.promo = ?
    """, (promo_id,))

    predefined_winner = cursor.fetchone()

    if not predefined_winner:
        await callback.answer("⚠ У этой акции нет назначенного победителя.")
        conn.close()
        return

    winner_name = predefined_winner[0]

    # Удаляем запись из predefined_winners
    cursor.execute("DELETE FROM predefined_winners WHERE promo = ?", (promo_id,))
    conn.commit()
    conn.close()

    admin_kb = await admin_kb_draw_()

    await callback.message.delete()
    await callback.message.answer(f"✅ Победитель @{winner_name} удалён из списка победителей.", reply_markup=admin_kb)
    await callback.answer()
    await state.set_state(AdminStates.admin_menu)


@router.message(AdminStates.edit_winners, F.text)
async def add_predefined_winner_input(message: Message, state: FSMContext):
    data = await state.get_data()
    promo_id = data.get("category_id")

    user_input = message.text.strip()
    conn = connect_db()
    cursor = conn.cursor()

    try:
        user_id = get_user(user_input)
    except:
        await message.answer("❌ Ошибка: Введите ID (число) или username в формате @username.")
        return

    if not user_id:
        await message.answer("❌ Пользователь не найден в базе данных.")
        conn.close()
        return

    cursor.execute("SELECT user_id FROM predefined_winners WHERE promo = ?", (promo_id,))
    existing_winner = cursor.fetchone()

    if existing_winner:
        await message.answer("⚠ Для этой акции уже назначен победитель. Удалите его перед добавлением нового.")
        conn.close()
        return

    # Добавляем нового победителя в predefined_winners
    cursor.execute("INSERT INTO predefined_winners (promo, user_id) VALUES (?, ?)", (promo_id, user_id))
    conn.commit()
    conn.close()

    promo_name = get_promo(promo_id)

    admin_kb = await admin_kb_draw_()
    await message.answer(f"✅ Пользователь успешно назначен победителем акции {promo_name}.")
    await message.answer("Меню админа и активные лотереи", reply_markup=admin_kb)
    await state.set_state(AdminStates.admin_menu)


@router.callback_query(F.data == "add_button", AdminStates.admin_menu)
async def add_lottery(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название лотереи")
    await state.set_state(AdminStates.add_category_name)
    await callback.answer()


@router.message(AdminStates.add_category_name, F.text)
async def input_lottery_name(message: Message, state: FSMContext):
    await state.update_data(promo_name=message.text)
    await message.answer('Введите стоимость 1 билета (более 50р)')
    await state.set_state(AdminStates.add_category_price)
#
#
# @router.message(AdminStates.add_category_end, F.text)
# async def input_lottery_end(message: Message, state: FSMContext):
#     try:
#         date_string = message.text.strip()
#
#         date_string = re.sub(r"[./]", "-", date_string)
#
#         # Конвертация в Unix Timestamp
#         unix_timestamp = int(datetime.strptime(date_string, "%d-%m-%Y").timestamp())
#
#         print(unix_timestamp)
#         await state.update_data(end_date=unix_timestamp)
#         await message.answer('Введите цену билета в рублях без копеек')
#         await state.set_state(AdminStates.add_category_price)
#
#     except ValueError:
#         await message.answer('❌ Неверный формат даты. Дата должна быть в формате `дд-мм-гггг`, например: 06-02-2025, 06.02.2025 или 06/02/2025.')


@router.message(AdminStates.add_category_price, F.text.isdigit())
async def input_lottery_price(message: Message, state: FSMContext):
    await state.update_data(ticket_price=message.text)
    await message.answer('Введите число билетов')
    await state.set_state(AdminStates.add_category_total_tickets)


@router.message(AdminStates.add_category_total_tickets, F.text.isdigit())
async def input_lottery_count(message: Message, state: FSMContext):
    await state.update_data(ticket_quantity=message.text)
    await state.set_state(AdminStates.add_category_total_play)
    await message.answer('Укажите число товаров (повторных розыгрышей)')


@router.message(AdminStates.add_category_total_play, F.text.isdigit())
async def input_lottery_total_play(message: Message, state: FSMContext):
    await state.update_data(count=message.text)
    await message.answer('Отправьте картинку лотереи')
    await state.set_state(AdminStates.add_category_img)


@router.message(AdminStates.add_category_img, F.content_type == ContentType.PHOTO)
async def input_lottery_img(message: Message, state: FSMContext):
    photo = message.photo[-1]
    print(photo)
    file_name = f"{photo.file_id}.jpg"
    file_path = MEDIA_DIR + file_name

    await state.update_data(img_id=photo.file_id)
    await state.update_data(img_url=file_path)

    lottery_create_data = await state.get_data()
    name = lottery_create_data['promo_name']
    # end = datetime.fromtimestamp(lottery_create_data['end_date']).strftime("%d.%m.%Y")
    count = lottery_create_data['count']
    price = lottery_create_data['ticket_price']
    quantity = lottery_create_data['ticket_quantity']

    await message.answer(f"Всё верно? \nНазвание: {name} \nТоваров: {count} \nЦена: {price} \nКоличество билетов: {quantity}",
                         reply_markup=create_confirm_kb)
    await state.set_state(AdminStates.add_category_accept)


@router.callback_query(F.data == "confirm_create", AdminStates.add_category_accept)
async def create_promo(callback: CallbackQuery, state: FSMContext):
    lottery_create_data = await state.get_data()

    name = lottery_create_data['promo_name']
    # end_date = lottery_create_data['end_date']  # UNIX-время
    ticket_price = lottery_create_data['ticket_price']
    ticket_quantity = lottery_create_data['ticket_quantity']
    count = lottery_create_data['count']
    file_id = lottery_create_data['img_id']
    path = lottery_create_data['img_url']

    # Округляем `end_date` до полуночи
    # end_datetime = datetime.fromtimestamp(end_date)
    # end_datetime = end_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
    # end_date_unix = int(end_datetime.timestamp())

    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO promo (category, start, end, ticket_price, total_tickets, remaining_tickets, img, played, total_play) 
            VALUES (?, strftime('%s', 'now'), ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, 2147483647, ticket_price, ticket_quantity, ticket_quantity, path, 0, count)
        )
        conn.commit()

        admin_kb = await admin_kb_draw_()

        await bot.download(file_id, destination=path)
        await callback.message.answer("✅ Лотерея успешно создана!", reply_markup=admin_kb)

    except sqlite3.Error as e:
        print(f"Ошибка при добавлении записи: {e}")
        await callback.message.answer("❌ Не удалось создать акцию. Попробуйте снова.")

    finally:
        conn.close()

    await state.clear()
    await state.set_state(AdminStates.admin_menu)
    await callback.answer()


@router.callback_query(F.data == "reject_create", AdminStates.add_category_accept)
async def decline_promo(callback: CallbackQuery, state: FSMContext):
    admin_kb = await admin_kb_draw_()

    await callback.message.answer("❌ Отмена создания", reply_markup=admin_kb)

    await state.clear()
    await state.set_state(AdminStates.admin_menu)
    await callback.answer()


