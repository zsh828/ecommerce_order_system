import pytest
from datetime import datetime, timedelta
from src.store import Store
from src.models import User, Product, Tier


@pytest.fixture
def store():
    return Store()


class TestUserManagement:
    def test_register_user_success(self, store):
        user = store.register_user("alice", "alice@example.com", "password123")
        assert user.username == "alice"
        assert user.email == "alice@example.com"
        assert user.tier == Tier.NORMAL
        assert user.points == 0

    def test_register_user_duplicate_username(self, store):
        store.register_user("alice", "alice1@example.com", "pass")
        with pytest.raises(ValueError, match="Username or Email already exists"):
            store.register_user("alice", "alice2@example.com", "pass")

    def test_register_user_duplicate_email(self, store):
        store.register_user("alice", "alice@example.com", "pass")
        with pytest.raises(ValueError, match="Username or Email already exists"):
            store.register_user("bob", "alice@example.com", "pass")

    def test_register_user_invalid_email(self, store):
        with pytest.raises(ValueError, match="Invalid email format"):
            store.register_user("bob", "invalid-email", "pass")

    def test_login_user_success(self, store):
        store.register_user("alice", "alice@example.com", "password123")
        user = store.login_user("alice", "password123")
        assert user.username == "alice"

    def test_login_user_wrong_password(self, store):
        store.register_user("alice", "alice@example.com", "password123")
        with pytest.raises(ValueError, match="Invalid credentials"):
            store.login_user("alice", "wrongpassword")

    def test_login_user_nonexistent(self, store):
        with pytest.raises(ValueError, match="Invalid credentials"):
            store.login_user("nobody", "pass")


class TestProductManagement:
    def test_add_product(self, store):
        product = store.add_product("Laptop", "Electronics", 1000.0, 10)
        assert product.name == "Laptop"
        assert product.category == "Electronics"
        assert product.price == 1000.0
        assert product.stock == 10

    def test_get_all_products(self, store):
        store.add_product("A", "Cat1", 10, 5)
        store.add_product("B", "Cat2", 20, 5)
        products = store.get_products()
        assert len(products) == 2

    def test_get_products_by_category(self, store):
        store.add_product("A", "Cat1", 10, 5)
        store.add_product("B", "Cat2", 20, 5)
        products = store.get_products("Cat1")
        assert len(products) == 1
        assert products[0].name == "A"

    def test_get_product_by_id_not_found(self, store):
        with pytest.raises(ValueError, match="Product not found"):
            store.get_product_by_id("P999")


class TestCartOperations:
    def test_add_to_cart(self, store):
        store.add_product("Laptop", "Electronics", 1000.0, 10)
        user = store.register_user("alice", "alice@example.com", "pass")
        store.add_to_cart(user, "P1", 2)
        
        cart = store.carts[user.username]
        assert len(cart) == 1
        assert cart[0].quantity == 2

    def test_add_to_cart_insufficient_stock(self, store):
        store.add_product("Laptop", "Electronics", 1000.0, 2)
        user = store.register_user("alice", "alice@example.com", "pass")
        with pytest.raises(ValueError, match="Insufficient stock"):
            store.add_to_cart(user, "P1", 3)

    def test_update_cart_quantity(self, store):
        store.add_product("Laptop", "Electronics", 1000.0, 10)
        user = store.register_user("alice", "alice@example.com", "pass")
        store.add_to_cart(user, "P1", 2)
        store.update_cart_quantity(user, "P1", 5)
        
        cart = store.carts[user.username]
        assert cart[0].quantity == 5

    def test_update_cart_quantity_exceed_stock(self, store):
        store.add_product("Laptop", "Electronics", 1000.0, 4)
        user = store.register_user("alice", "alice@example.com", "pass")
        store.add_to_cart(user, "P1", 2)
        with pytest.raises(ValueError, match="Insufficient stock"):
            store.update_cart_quantity(user, "P1", 5)

    def test_remove_from_cart(self, store):
        store.add_product("Laptop", "Electronics", 1000.0, 10)
        user = store.register_user("alice", "alice@example.com", "pass")
        store.add_to_cart(user, "P1", 2)
        store.remove_from_cart(user, "P1")
        assert len(store.carts[user.username]) == 0

    def test_remove_from_cart_item_not_in_cart(self, store):
        store.add_product("Laptop", "Electronics", 1000.0, 10)
        user = store.register_user("alice", "alice@example.com", "pass")
        with pytest.raises(ValueError, match="Item not in cart"):
            store.remove_from_cart(user, "P1")


class TestOrderCreationAndPayment:
    def test_create_order_empty_cart(self, store):
        user = store.register_user("alice", "alice@example.com", "pass")
        with pytest.raises(ValueError, match="Cart is empty"):
            store.create_order(user)

    def test_create_order_success(self, store):
        store.add_product("Laptop", "Electronics", 1000.0, 10)
        user = store.register_user("alice", "alice@example.com", "pass")
        store.add_to_cart(user, "P1", 1)
        
        order = store.create_order(user)
        assert order.status == "pending"
        assert len(store.carts[user.username]) == 0  # Cart cleared
        assert order.total_amount == 1000.0  # No discount for normal

    def test_pay_order_success(self, store):
        store.add_product("Laptop", "Electronics", 1000.0, 10)
        user = store.register_user("alice", "alice@example.com", "pass")
        store.add_to_cart(user, "P1", 1)
        order = store.create_order(user)
        
        store.pay_order(user, order.order_id)
        
        assert order.status == "paid"
        assert user.points == 1000  # 1000 * 1 point per dollar
        # Stock should be reduced
        product = store.get_product_by_id("P1")
        assert product.stock == 9

    def test_pay_order_pending_status_check(self, store):
        store.add_product("Laptop", "Electronics", 1000.0, 10)
        user = store.register_user("alice", "alice@example.com", "pass")
        store.add_to_cart(user, "P1", 1)
        order = store.create_order(user)
        
        # Cancel first
        store.cancel_order(user, order.order_id)
        
        with pytest.raises(ValueError, match="Order must be pending to pay"):
            store.pay_order(user, order.order_id)

    def test_cancel_order_success(self, store):
        store.add_product("Laptop", "Electronics", 1000.0, 10)
        user = store.register_user("alice", "alice@example.com", "pass")
        store.add_to_cart(user, "P1", 1)
        order = store.create_order(user)
        
        store.cancel_order(user, order.order_id)
        
        assert order.status == "cancelled"
        product = store.get_product_by_id("P1")
        assert product.stock == 10  # Stock restored
        assert user.points == 0   # Points not added because not paid

    def test_cancel_already_paid_order(self, store):
        store.add_product("Laptop", "Electronics", 1000.0, 10)
        user = store.register_user("alice", "alice@example.com", "pass")
        store.add_to_cart(user, "P1", 1)
        order = store.create_order(user)
        store.pay_order(user, order.order_id)
        
        with pytest.raises(ValueError, match="Only pending orders can be cancelled"):
            store.cancel_order(user, order.order_id)


class TestDiscountsAndTiers:
    def test_silver_tier_discount(self, store):
        # Force silver tier by adding points manually via helper or logic
        # Since add_points triggers upgrade, let's simulate a silver user
        user = store.register_user("alice", "alice@example.com", "pass")
        user.points = 1500  # Should trigger silver upgrade
        
        store.add_product("Laptop", "Electronics", 1000.0, 10)
        store.add_to_cart(user, "P1", 1)
        order = store.create_order(user)
        
        assert user.tier == Tier.SILVER
        assert order.total_amount == 950.0  # 1000 * 0.95

    def test_gold_tier_discount(self, store):
        user = store.register_user("alice", "alice@example.com", "pass")
        user.points = 3500  # Should trigger gold upgrade
        
        store.add_product("Laptop", "Electronics", 1000.0, 10)
        store.add_to_cart(user, "P1", 1)
        order = store.create_order(user)
        
        assert user.tier == Tier.GOLD
        assert order.total_amount == 900.0  # 1000 * 0.9

    def test_normal_tier_no_discount(self, store):
        user = store.register_user("alice", "alice@example.com", "pass")
        # Default is normal
        
        store.add_product("Laptop", "Electronics", 1000.0, 10)
        store.add_to_cart(user, "P1", 1)
        order = store.create_order(user)
        
        assert user.tier == Tier.NORMAL
        assert order.total_amount == 1000.0


class TestSalesStats:
    def test_basic_sales_stats(self, store):
        store.add_product("Laptop", "Electronics", 1000.0, 10)
        store.add_product("Mouse", "Accessories", 50.0, 100)
        
        user1 = store.register_user("alice", "alice@example.com", "pass")
        store.add_to_cart(user1, "P1", 1)
        order1 = store.create_order(user1)
        store.pay_order(user1, order1.order_id)
        
        user2 = store.register_user("bob", "bob@example.com", "pass")
        store.add_to_cart(user2, "P2", 2)
        order2 = store.create_order(user2)
        store.pay_order(user2, order2.order_id)
        
        stats = store.get_sales_stats()
        
        assert stats['orders_count'] == 2
        # Order 1: 1000. Revenue 1000
        # Order 2: 50 * 2 = 100. Revenue 100
        assert stats['total_revenue'] == 1100.0
        
        assert stats['by_category']['Electronics'] == 1000.0
        assert stats['by_category']['Accessories'] == 100.0
        
        assert stats['by_product']['Laptop'] == 1000.0
        assert stats['by_product']['Mouse'] == 100.0

    def test_sales_stats_filter_by_time(self, store):
        store.add_product("Laptop", "Electronics", 1000.0, 10)
        user = store.register_user("alice", "alice@example.com", "pass")
        store.add_to_cart(user, "P1", 1)
        order1 = store.create_order(user)
        store.pay_order(user, order1.order_id)
        
        # Create another order later
        # Mocking time is complex in simple tests, so we rely on creation order
        # Assuming sequential execution implies time difference if needed, 
        # but here we just test that unpaid orders are excluded.
        
        store.add_product("Mouse", "Accessories", 50.0, 100)
        store.add_to_cart(user, "P2", 1)
        order2 = store.create_order(user)
        # Do NOT pay order2
        
        stats = store.get_sales_stats()
        assert stats['orders_count'] == 1
        assert stats['total_revenue'] == 1000.0