from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db import connect_db
import time
from aiogram.filters.callback_data import CallbackData


back_button = [InlineKeyboardButton(text='Назад', callback_data='back_button')]


async def admin_kb_draw_():
    conn = connect_db()
    cursor = conn.cursor()

    current_time = int(time.time())
    cursor.execute("SELECT * FROM promo WHERE played < total_play")
    categories = cursor.fetchall()

    conn.close()

    add_admin_button = InlineKeyboardButton(text='Добавить администратора', callback_data='add_admin')
    remove_admin_button = InlineKeyboardButton(text='Удалить администратора', callback_data='remove_admin')

    admins_control_buttons = [add_admin_button, remove_admin_button]  # Объединяем в один список (один ряд)

    category_buttons = [
        [InlineKeyboardButton(text=f"{category[1]}", callback_data=f"ticket_category_{category[0]}")]
        for category in categories
    ]

    add_button = [InlineKeyboardButton(text='Добавить лотерею', callback_data='add_button')]

    category_buttons.append(admins_control_buttons)
    category_buttons.append(add_button)

    return InlineKeyboardMarkup(inline_keyboard=category_buttons)


async def current_admins():
    """Создает клавиатуру с администраторами"""
    conn = connect_db()
    cursor = conn.cursor()

    # Получаем список админов
    cursor.execute("SELECT COALESCE(telegram_name, telegram_id), telegram_id FROM admins")
    admins = cursor.fetchall()
    conn.close()

    # Если админов нет, возвращаем сообщение
    if not admins:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Администраторы не найдены", callback_data="none")]
        ])

    # Создаём кнопки
    admin_buttons = [
        [InlineKeyboardButton(text=f"👤 {admin[0]}", callback_data=f"admin_{admin[1]}")]
        for admin in admins
    ]

    return InlineKeyboardMarkup(inline_keyboard=admin_buttons)



create_confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Да', callback_data='confirm_create')],
    [InlineKeyboardButton(text='Нет', callback_data='reject_create')]
])

edit_lottery_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Название', callback_data='edit_name')],
    [InlineKeyboardButton(text='Число билетов', callback_data='edit_total_tickets')],
    [InlineKeyboardButton(text='Стоимость билетов', callback_data='edit_price')],
    [InlineKeyboardButton(text='Число товаров', callback_data='edit_count')],
    [InlineKeyboardButton(text='➖Удалить победителя', callback_data='remove_predefined_winner'),
     InlineKeyboardButton(text='➕Добавить победителя', callback_data='add_predefined_winner')],
    [InlineKeyboardButton(text='Удалить лотерею', callback_data='remove_lottery')],
    back_button
])

remove_confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Да', callback_data='confirm_remove')],
    [InlineKeyboardButton(text='Нет', callback_data='back_button')]
])
