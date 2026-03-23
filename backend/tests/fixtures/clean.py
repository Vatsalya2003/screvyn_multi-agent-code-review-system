# Test fixture: clean, well-written Python code
import os
import sqlite3
from dataclasses import dataclass
from typing import Optional

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")


@dataclass
class User:
    id: int
    name: str
    email: str


class UserRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_by_id(self, user_id: int) -> Optional[User]:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT id, name, email FROM users WHERE id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return User(id=row[0], name=row[1], email=row[2])
        finally:
            conn.close()

    def get_by_ids(self, user_ids: list[int]) -> list[User]:
        if not user_ids:
            return []
        conn = sqlite3.connect(self.db_path)
        try:
            placeholders = ",".join("?" for _ in user_ids)
            cursor = conn.execute(
                f"SELECT id, name, email FROM users WHERE id IN ({placeholders})",
                user_ids,
            )
            return [User(id=r[0], name=r[1], email=r[2]) for r in cursor.fetchall()]
        finally:
            conn.close()


DISCOUNT_THRESHOLDS = [
    (1000, 0.15),
    (500, 0.10),
    (0, 0.05),
]


def calculate_discount(price: float) -> float:
    for threshold, rate in DISCOUNT_THRESHOLDS:
        if price > threshold:
            return price * rate
    return 0.0
PYEOFcat > backend/tests/fixtures/clean.py << 'PYEOF'
# Test fixture: clean, well-written Python code
import os
import sqlite3
from dataclasses import dataclass
from typing import Optional

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")


@dataclass
class User:
    id: int
    name: str
    email: str


class UserRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_by_id(self, user_id: int) -> Optional[User]:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT id, name, email FROM users WHERE id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return User(id=row[0], name=row[1], email=row[2])
        finally:
            conn.close()

    def get_by_ids(self, user_ids: list[int]) -> list[User]:
        if not user_ids:
            return []
        conn = sqlite3.connect(self.db_path)
        try:
            placeholders = ",".join("?" for _ in user_ids)
            cursor = conn.execute(
                f"SELECT id, name, email FROM users WHERE id IN ({placeholders})",
                user_ids,
            )
            return [User(id=r[0], name=r[1], email=r[2]) for r in cursor.fetchall()]
        finally:
            conn.close()


DISCOUNT_THRESHOLDS = [
    (1000, 0.15),
    (500, 0.10),
    (0, 0.05),
]


def calculate_discount(price: float) -> float:
    for threshold, rate in DISCOUNT_THRESHOLDS:
        if price > threshold:
            return price * rate
    return 0.0
