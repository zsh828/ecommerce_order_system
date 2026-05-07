import hashlib
import os
import re
from datetime import datetime
from enum import Enum


class Tier(Enum):
    NORMAL = "normal"
    SILVER = "silver"
    GOLD = "gold"


class ProductStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class OrderStatus(Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


def hash_password(password: str, salt: str = None) -> tuple:
    """Hash password with salt."""
    if salt is None:
        salt = hashlib.sha256(os.urandom(32)).hexdigest()
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return key.hex(), salt


def verify_password(password: str, stored_key: str, salt: str) -> bool:
    """Verify password against stored hash."""
    new_key, _ = hash_password(password, salt)
    return new_key == stored_key


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))


class User:
    def __init__(self, user_id: int, username: str, email: str, password_hash: str, salt: str, tier: Tier = Tier.NORMAL, points: int = 0):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.salt = salt
        self.tier = tier
        self.points = points

    def add_points(self, amount: int):
        self.points += amount
        self._check_tier_upgrade()

    def _check_tier_upgrade(self):
        if self.tier == Tier.NORMAL and self.points >= 1000:
            self.tier = Tier.SILVER
        elif self.tier == Tier.SILVER and self.points >= 5000:
            self.tier = Tier.GOLD

    def get_discount_rate(self) -> float:
        if self.tier == Tier.GOLD:
            return 0.9
        elif self.tier == Tier.SILVER:
            return 0.95
        return 1.0


class Product:
    def __init__(self, product_id: int, name: str, price: float, category: str, stock: int):
        self.product_id = product_id
        self.name = name
        self.price = price
        self.category = category
        self.stock = stock
        self.status = ProductStatus.ACTIVE

    def update_stock(self, quantity: int):
        self.stock += quantity

    def check_availability(self, quantity: int) -> bool:
        return self.stock >= quantity and self.status == ProductStatus.ACTIVE


class CartItem:
    def __init__(self, product: Product, quantity: int):
        self.product = product
        self.quantity = quantity

    @property
    def total_price(self):
        return self.product.price * self.quantity


class Order:
    def __init__(self, order_id: int, user: User, items: list, status: OrderStatus = OrderStatus.PENDING):
        self.order_id = order_id
        self.user = user
        self.items = items  # List of CartItem
        self.status = status
        self.created_at = datetime.now()
        self.total_amount = self._calculate_total()

    def _calculate_total(self) -> float:
        subtotal = sum(item.total_price for item in self.items)
        discount_rate = self.user.get_discount_rate()
        return round(subtotal * discount_rate, 2)

    def cancel(self):
        if self.status == OrderStatus.PAID:
            self.status = OrderStatus.CANCELLED
            return True
        return False