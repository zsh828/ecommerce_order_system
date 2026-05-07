import pytest
from src.models import (
    User, Product, CartItem, Order, Tier, OrderStatus, 
    validate_email, hash_password, verify_password
)
from datetime import datetime


class TestUserModel:
    def test_initialization(self):
        user = User(1, "testuser", "test@example.com", "hash", "salt", Tier.NORMAL, 0)
        assert user.user_id == 1
        assert user.username == "testuser"
        assert user.tier == Tier.NORMAL
        assert user.points == 0

    def test_add_points_normal_to_silver(self):
        user = User(1, "testuser", "test@example.com", "hash", "salt", Tier.NORMAL, 0)
        user.add_points(1000)
        assert user.tier == Tier.SILVER
        assert user.points == 1000

    def test_add_points_silver_to_gold(self):
        user = User(1, "testuser", "test@example.com", "hash", "salt", Tier.SILVER, 4000)
        user.add_points(1000)
        assert user.tier == Tier.GOLD
        assert user.points == 5000

    def test_get_discount_rate_normal(self):
        user = User(1, "testuser", "test@example.com", "hash", "salt", Tier.NORMAL, 0)
        assert user.get_discount_rate() == 1.0

    def test_get_discount_rate_silver(self):
        user = User(1, "testuser", "test@example.com", "hash", "salt", Tier.SILVER, 0)
        assert user.get_discount_rate() == 0.95

    def test_get_discount_rate_gold(self):
        user = User(1, "testuser", "test@example.com", "hash", "salt", Tier.GOLD, 0)
        assert user.get_discount_rate() == 0.9


class TestProductModel:
    def test_check_availability_true(self):
        product = Product(1, "Test", 10.0, "Cat", 5)
        assert product.check_availability(3) is True

    def test_check_availability_false_insufficient_stock(self):
        product = Product(1, "Test", 10.0, "Cat", 2)
        assert product.check_availability(3) is False

    def test_check_availability_false_inactive(self):
        product = Product(1, "Test", 10.0, "Cat", 5)
        product.status = ProductStatus.INACTIVE
        assert product.check_availability(1) is False

    def test_update_stock_increase(self):
        product = Product(1, "Test", 10.0, "Cat", 5)
        product.update_stock(3)
        assert product.stock == 8

    def test_update_stock_decrease(self):
        product = Product(1, "Test", 10.0, "Cat", 5)
        product.update_stock(-2)
        assert product.stock == 3


class TestCartItemModel:
    def test_total_price_calculation(self):
        product = Product(1, "Test", 10.0, "Cat", 10)
        item = CartItem(product, 3)
        assert item.total_price == 30.0


class TestOrderModel:
    def test_calculate_total_no_discount(self):
        user = User(1, "u", "e@e.com", "h", "s", Tier.NORMAL, 0)
        product = Product(1, "P", 10.0, "C", 10)
        item = CartItem(product, 2)
        order = Order(1, user, [item])
        assert order.total_amount == 20.0

    def test_calculate_total_silver_discount(self):
        user = User(1, "u", "e@e.com", "h", "s", Tier.SILVER, 0)
        product = Product(1, "P", 10.0, "C", 10)
        item = CartItem(product, 2)
        order = Order(1, user, [item])
        assert order.total_amount == 19.0  # 20 * 0.95

    def test_cancel_paid_order(self):
        user = User(1, "u", "e@e.com", "h", "s", Tier.NORMAL, 0)
        product = Product(1, "P", 10.0, "C", 10)
        item = CartItem(product, 2)
        order = Order(1, user, [item], OrderStatus.PAID)
        result = order.cancel()
        assert result is True
        assert order.status == OrderStatus.CANCELLED

    def test_cancel_pending_order_fails(self):
        user = User(1, "u", "e@e.com", "h", "s", Tier.NORMAL, 0)
        product = Product(1, "P", 10.0, "C", 10)
        item = CartItem(product, 2)
        order = Order(1, user, [item], OrderStatus.PENDING)
        result = order.cancel()
        assert result is False
        assert order.status == OrderStatus.PENDING


class TestValidationFunctions:
    def test_validate_email_valid(self):
        assert validate_email("user@example.com") is True

    def test_validate_email_invalid_no_at(self):
        assert validate_email("userexample.com") is False

    def test_validate_email_invalid_no_domain(self):
        assert validate_email("@example.com") is False

    def test_hash_and_verify_password(self):
        pwd = "securepassword"
        h, s = hash_password(pwd)
        assert verify_password(pwd, h, s) is True
        assert verify_password("wrongpassword", h, s) is False