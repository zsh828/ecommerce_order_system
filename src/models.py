import hashlib
import re
from datetime import datetime
from enum import Enum


class Tier(Enum):
    NORMAL = "normal"
    SILVER = "silver"
    GOLD = "gold"


class User:
    def __init__(self, username: str, email: str, password: str):
        if not self._validate_email(email):
            raise ValueError("Invalid email format")
        
        self.username = username
        self.email = email
        self.password_hash = self._hash_password(password)
        self.tier = Tier.NORMAL
        self.points = 0
        self.created_at = datetime.now()

    @staticmethod
    def _validate_email(email: str) -> bool:
        pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        return bool(re.match(pattern, email))

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password: str) -> bool:
        return self.password_hash == self._hash_password(password)

    def add_points(self, amount: int):
        if amount < 0:
            raise ValueError("Points cannot be negative")
        self.points += amount
        self._check_tier_upgrade()

    def _check_tier_upgrade(self):
        # Logic for tier upgrade based on points
        # Normal -> Silver: 1000 points
        # Silver -> Gold: 3000 points
        if self.points >= 3000 and self.tier != Tier.GOLD:
            self.tier = Tier.GOLD
        elif self.points >= 1000 and self.tier != Tier.SILVER:
            self.tier = Tier.SILVER

    def get_discount_rate(self) -> float:
        if self.tier == Tier.GOLD:
            return 0.9
        elif self.tier == Tier.SILVER:
            return 0.95
        else:
            return 1.0


class Product:
    def __init__(self, product_id: str, name: str, category: str, price: float, stock: int):
        self.product_id = product_id
        self.name = name
        self.category = category
        self.price = price
        self.stock = stock

    def is_available(self) -> bool:
        return self.stock > 0

    def decrease_stock(self, quantity: int):
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")
        if quantity > self.stock:
            raise ValueError("Insufficient stock")
        self.stock -= quantity

    def increase_stock(self, quantity: int):
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")
        self.stock += quantity


class OrderItem:
    def __init__(self, product: Product, quantity: int):
        self.product = product
        self.quantity = quantity
        self.unit_price = product.price

    def get_subtotal(self) -> float:
        return self.unit_price * self.quantity


class Order:
    def __init__(self, order_id: str, user: User, items: list[OrderItem]):
        self.order_id = order_id
        self.user = user
        self.items = items
        self.status = "pending"  # pending, paid, cancelled
        self.created_at = datetime.now()
        self.total_amount = self._calculate_total()

    def _calculate_total(self) -> float:
        subtotal = sum(item.get_subtotal() for item in self.items)
        discount_rate = self.user.get_discount_rate()
        return subtotal * discount_rate

    def cancel(self):
        if self.status != "pending":
            raise ValueError("Only pending orders can be cancelled")
        self.status = "cancelled"
        # Restore stock
        for item in self.items:
            item.product.increase_stock(item.quantity)

    def pay(self):
        if self.status != "pending":
            raise ValueError("Order must be pending to pay")
        self.status = "paid"
        # Add points to user
        self.user.add_points(int(self.total_amount))
        # Note: Stock deduction happens at order creation time now