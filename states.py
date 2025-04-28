from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

storage = MemoryStorage()


class ClientStates(StatesGroup):
    main_menu = State()
    shop_menu = State()
    product_info = State()
    promo_menu = State()
    promo_info = State()

    profile_menu = State()
    edit_name = State()
    edit_city = State()
    edit_address = State()
    edit_phone = State()
    edit_email = State()

class AdminStates(StatesGroup):
    admin_menu = State()
    add_category_name = State()
    add_category_end = State()
    add_category_price = State()
    add_category_total_tickets = State()
    add_category_total_play = State()
    add_category_img = State()
    add_category_accept = State()

    add_new_admin = State()
    remove_admin = State()

    edit_categories = State()
    edit_winners = State()
    edit_name = State()
    edit_ticket_count = State()
    edit_ticket_price = State()
    edit_end_date = State()
    edit_count = State()
