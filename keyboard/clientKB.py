from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db import connect_db
import time
from aiogram.filters.callback_data import CallbackData

profile_button = InlineKeyboardButton(text="Зарегистрируйся для участия", callback_data='profile_open')
single_profile_kb = InlineKeyboardMarkup(inline_keyboard=[[profile_button]])

user_url = f"https://t.me/festivalChat1"
user_link_button = InlineKeyboardButton(text="Наши победители", url=user_url)
# InlineKeyboardButton(text="Информация", callback_data='lottery_info')
main_menu_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="ЖМИ и ВЫИГРЫВАЙ", callback_data='lottery_categories'),
    user_link_button],
    [profile_button]
])


back_button = [InlineKeyboardButton(text='Назад', callback_data='back_button')]
back_kb = InlineKeyboardMarkup(inline_keyboard=[back_button])

profile_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Имя", callback_data="edit_name"),
     InlineKeyboardButton(text='Номер телефона', callback_data='edit_phone'),
     InlineKeyboardButton(text="Email", callback_data="edit_email")],
    [InlineKeyboardButton(text="Город", callback_data="edit_city"),
     ],
    back_button
])
# InlineKeyboardButton(text="Адрес", callback_data="edit_address")
async def create_shop_kb():
    conn = connect_db()
    cursor = conn.cursor()

    current_time = int(time.time())
    cursor.execute("SELECT * FROM products")
    # id, name, desc, price = cursor.fetchall()
    products = cursor.fetchall()
    product_buttons = [
        [InlineKeyboardButton(text=f"{product[1]}", callback_data=f"product_id_{product[0]}")]
        for product in products
    ]
    conn.close()
    product_buttons.append(back_button)

    return InlineKeyboardMarkup(inline_keyboard=product_buttons)


def draw_product_buy(price, p_id):
    product_buttons = []
    product_buttons.append([InlineKeyboardButton(text=f'Купить за {price}₽', callback_data=f'buy_product_{p_id}')])
    product_buttons.append(back_button)
    return InlineKeyboardMarkup(inline_keyboard=product_buttons)


async def categories_kb_draw():
    conn = connect_db()
    cursor = conn.cursor()

    current_time = int(time.time())
    cursor.execute("SELECT * FROM promo WHERE played < total_play")
    categories = cursor.fetchall()

    conn.close()

    category_buttons = [
        [InlineKeyboardButton(text=f"{category[1]}", callback_data=f"ticket_category_{category[0]}")]
        for category in categories
    ]
    shop = InlineKeyboardButton(text="Магазин сувениров", callback_data='shop')


    category_buttons.append([shop])

    category_buttons.append(back_button)

    return InlineKeyboardMarkup(inline_keyboard=category_buttons)


class TicketCallback(CallbackData, prefix="ticket"):
    quantity: int
    price: int


async def tickets_kb_draw(promo_id):
    conn = connect_db()
    cursor = conn.cursor()

    # Используем fetchone() для получения одной записи
    cursor.execute("SELECT ticket_price FROM promo WHERE id = ?", (promo_id,))
    promo = cursor.fetchone()
    conn.close()

    promo_info_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f'1 постер за {promo[0]}₽',
                              callback_data=TicketCallback(quantity=1, price=promo[0]*1).pack())],
        [InlineKeyboardButton(text=f'3 постера за {promo[0]*3}₽',
                              callback_data=TicketCallback(quantity=3, price=promo[0]*3).pack())],
        [InlineKeyboardButton(text=f'5 постеров за {promo[0]*5}₽',
                              callback_data=TicketCallback(quantity=5, price=promo[0]*5).pack())],
        back_button
    ])

    return promo_info_kb
cancel_payment_button = InlineKeyboardButton(text='✖️ Отменить платёж', callback_data='cancel_payment')
cancel_payment_kb = InlineKeyboardMarkup(inline_keyboard=[
    [cancel_payment_button]
])
