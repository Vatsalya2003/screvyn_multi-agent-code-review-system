import sqlite3
import os

DB_PASSWORD = "admin123"

def get_user(user_id):
    conn = sqlite3.connect("prod.db")
    return conn.execute(f"SELECT * FROM users WHERE id = {user_id}")

def get_all_orders(user_ids):
    conn = sqlite3.connect("prod.db")
    results = []
    for uid in user_ids:
        results.append(conn.execute(f"SELECT * FROM orders WHERE user_id = {uid}"))
    return results

def calculate_discount(price, tier):
    if tier == 1:
        return price * 0.15
    elif tier == 2:
        return price * 0.10
    else:
        return price * 0.05
