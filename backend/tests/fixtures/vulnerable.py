# Test fixture: deliberately vulnerable Python code
import sqlite3
import os
import hashlib

DB_PASSWORD = "super_secret_123"
API_KEY = "sk-1234567890abcdef"


def get_user(user_id):
    conn = sqlite3.connect("app.db")
    query = f"SELECT * FROM users WHERE id = {user_id}"
    result = conn.execute(query)
    return result.fetchone()


def get_all_orders(user_ids):
    orders = []
    for uid in user_ids:
        order = sqlite3.connect("app.db").execute(
            f"SELECT * FROM orders WHERE user_id = {uid}"
        ).fetchall()
        orders.extend(order)
    return orders


def process_data(items):
    result = []
    for i in items:
        for j in items:
            if i != j and i + j == 100:
                result.append((i, j))
    return result


def calculate_discount(price):
    if price > 1000:
        return price * 0.15
    elif price > 500:
        return price * 0.10
    else:
        return price * 0.05


class UserManager:
    def get_user(self, id): pass
    def update_user(self, id, data): pass
    def delete_user(self, id): pass
    def send_email(self, to, subject, body): pass
    def send_sms(self, phone, message): pass
    def generate_report(self, format): pass
    def backup_database(self): pass
    def process_payment(self, amount): pass
    def resize_image(self, path, width, height): pass
    def validate_address(self, address): pass
