import sqlite3


def connect_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_all_users() -> set:
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id FROM users")
    users = {row[0] for row in cursor.fetchall()}
    conn.close()
    return users


def get_user(user_input):
    conn = connect_db()
    cursor = conn.cursor()
    print(user_input)
    try:
        # Проверяем, является ли telegram_id числом
        if isinstance(user_input, int) or user_input.isdigit():
            cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (int(user_input),))
        else:
            user_input = user_input[1:]
            cursor.execute("SELECT id FROM users WHERE telegram_name = ?", (user_input,))

        user_data = cursor.fetchone()
        return user_data[0] if user_data else None  # Если пользователя нет, возвращаем None

    except Exception as e:
        print(f"Ошибка в get_user: {e}")
        return None

    finally:
        conn.close()


def get_admin(user_input):
    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Проверяем, является ли telegram_id числом
        if isinstance(user_input, int) or user_input.isdigit():
            cursor.execute("SELECT id FROM admins WHERE telegram_id = ?", (int(user_input),))
        else:
            user_input = user_input[1:]
            cursor.execute("SELECT id FROM admins WHERE telegram_name = ?", (user_input,))

        user_data = cursor.fetchone()
        return user_data[0] if user_data else None  # Если пользователя нет, возвращаем None

    except Exception as e:
        print(f"Ошибка в get_user: {e}")
        return None

    finally:
        conn.close()


def get_user_telegram_id(user_input):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        # Проверяем, является ли telegram_id числом
        cursor.execute("SELECT telegram_id FROM users WHERE id = ?", (int(user_input),))

        user_data = cursor.fetchone()
        return user_data[0] if user_data else None  # Если пользователя нет, возвращаем None

    except Exception as e:
        print(f"Ошибка в get_user: {e}")
        return None

    finally:
        conn.close()


def get_user_full_info(user_input):
    conn = connect_db()
    cursor = conn.cursor()
    print(user_input)

    try:
        # Проверяем, является ли telegram_id числом
        if isinstance(user_input, int) or user_input.isdigit():
            cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (int(user_input),))
        else:
            user_input = user_input[1:]
            cursor.execute("SELECT * FROM users WHERE telegram_name = ?", (user_input,))

        user_data = cursor.fetchone()
        return user_data if user_data else None  # Возвращаем полный набор данных пользователя

    except Exception as e:
        print(f"Ошибка в get_user_full_info: {e}")
        return None

    finally:
        conn.close()


def get_promo(promo_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT category FROM promo WHERE id = ?", (promo_id,))
    category_name = cursor.fetchone()[0]
    return category_name


user_cache = get_all_users()
