import sqlite3
from db import connect_db
import time

conn = connect_db()
cursor = conn.cursor()

try:
    cursor.execute("INSERT INTO admins (telegram_id, telegram_name) VALUES (?, ?)", (571294067, 'burzhuykaa'))
    conn.commit()
except sqlite3.IntegrityError as e:
    print(f"Ошибка: {e}")  # Если FOREIGN KEY не найден, тут будет ошибка


def add_promo(category: str, start: int, end: int):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO promo (category, start, end)
        VALUES (?, ?, ?)
    """, (category, start, end))

    conn.commit()
    conn.close()


def add_product(desc: str, price: int):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO products (desc, price)
        VALUES (?, ?)
    """, (desc, price,))

    conn.commit()
    conn.close()



# name = 'Машина'
# time_start = int(time.time())
# time_end = int(time.time() + 100000)
# for i in range(4, 10):
#     add_product(i, i)
#add_promo(name, time_start, time_end)
