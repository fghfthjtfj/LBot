from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from db import get_user
from keyboard.clientKB import *
from states import ClientStates

router = Router()


@router.callback_query(F.data == "profile_open", ClientStates.main_menu)
async def profile(callback: CallbackQuery, state: FSMContext):
    user_id = get_user(callback.from_user.id)
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT name, city, address, phone, email FROM users WHERE id = ?", (user_id,))
    profile_data = cursor.fetchone()
    conn.close()

    # Гарантированное заполнение значений
    name, city, address, phone, email = (profile_data or (None, None, None, None, None))
    name = name if name else "Не указано"
    city = city if city else "Не указано"
    address = address if address else "Не указано"
    phone = phone if phone else "Не указано"
    email = email if email else "Не указано"
    await state.update_data(user_id=user_id, name=name, city=city, address=address, phone=phone, email=email)

    await callback.message.edit_text(
        f"📜 **Ваш профиль:**\n"
        f"👤 Имя: {name}\n"
        f"🏙 Город: {city}\n"
        f"📞 Телефон: {phone}\n"
        f"📧 Email: {email}",
        reply_markup=profile_kb
    )
    #         f"🏠 Адрес: {address} (Не обязательно)\n"
    await state.set_state(ClientStates.profile_menu)
    await callback.answer()


async def update_profile_field(message: Message, state: FSMContext, field_name: str, new_value: str):
    """Обновляет одно поле в профиле и отправляет обновлённый профиль"""
    data = await state.get_data()
    user_id = data["user_id"]

    # Гарантированное заполнение значений
    name = data.get("name", "Не указано")
    city = data.get("city", "Не указано")
    address = data.get("address", "Не указано")
    phone = data.get("phone", "Не указано")
    email = data.get("email", "Не указано")

    # Русские названия для полей
    field_names_rus = {
        "name": "Имя",
        "city": "Город",
        "address": "Адрес",
        "phone": "Телефон",
        "email": "Email"
    }

    # Обновляем соответствующее поле
    if field_name == "name":
        name = new_value
    elif field_name == "city":
        city = new_value
    elif field_name == "address":
        address = new_value
    elif field_name == "phone":
        phone = new_value
    elif field_name == "email":
        email = new_value

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {field_name} = ? WHERE id = ?", (new_value, user_id))
    conn.commit()
    conn.close()

    await message.answer(
        f"✅ {field_names_rus[field_name]} успешно обновлено!\n\n"
        f"📜 **Ваш профиль:**\n"
        f"👤 Имя: {name}\n"
        f"🏙 Город: {city}\n"
        f"📞 Телефон: {phone}\n"
        f"📧 Email: {email}",
        reply_markup=profile_kb
    )
    # f"🏠 Адрес: {address}\n"

    await state.update_data(**{field_name: new_value})
    await state.set_state(ClientStates.profile_menu)


@router.callback_query(F.data == "edit_name", ClientStates.profile_menu)
async def edit_name_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите Имя одним сообщением")
    await state.set_state(ClientStates.edit_name)
    await callback.answer()


@router.message(ClientStates.edit_name, F.text)
async def edit_name(message: Message, state: FSMContext):
    await update_profile_field(message, state, "name", message.text.strip())


@router.callback_query(F.data == "edit_city", ClientStates.profile_menu)
async def edit_city_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите ваш город одним сообщением")
    await state.set_state(ClientStates.edit_city)
    await callback.answer()


@router.message(ClientStates.edit_city, F.text)
async def edit_city(message: Message, state: FSMContext):
    await update_profile_field(message, state, "city", message.text.strip())


@router.callback_query(F.data == "edit_address", ClientStates.profile_menu)
async def edit_address_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите ваш адрес одним сообщением")
    await state.set_state(ClientStates.edit_address)
    await callback.answer()


@router.message(ClientStates.edit_address, F.text)
async def edit_address(message: Message, state: FSMContext):
    await update_profile_field(message, state, "address", message.text.strip())


@router.callback_query(F.data == "edit_phone", ClientStates.profile_menu)
async def edit_phone_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите ваш номер телефона одним сообщением")
    await state.set_state(ClientStates.edit_phone)
    await callback.answer()


@router.message(ClientStates.edit_phone, F.text)
async def edit_phone(message: Message, state: FSMContext):
    await update_profile_field(message, state, "phone", message.text.strip())


@router.callback_query(F.data == "edit_email", ClientStates.profile_menu)
async def edit_email_callback(callback: CallbackQuery, state: FSMContext):
    """Запрос ввода нового email"""
    await callback.message.edit_text("Введите ваш email одним сообщением")
    await state.set_state(ClientStates.edit_email)
    await callback.answer()


@router.message(ClientStates.edit_email, F.text)
async def edit_email(message: Message, state: FSMContext):
    """Обновление email"""
    new_email = message.text.strip()

    # Простая проверка на корректность email
    if "@" not in new_email or "." not in new_email:
        await message.answer("⚠ Пожалуйста, введите корректный email.")
        return

    await update_profile_field(message, state, "email", new_email)

