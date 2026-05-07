import pytest
from datetime import datetime, timedelta
from src.services import UserService, ProductService, CartService, OrderService
from src.models import Tier, ProductStatus


class TestUserService:
    def setup_method(self):
        self.service = UserService()

    def test_register_success(self):
        user = self.service.register("alice", "alice@test.com", "pass123")
        assert user.username == "alice"
        assert user.tier == Tier.NORMAL
        assert user.points == 0

    def test_register_duplicate_username(self):
        self.service.register("alice", "alice@test.com", "pass123")
        with pytest.raises(ValueError, match="Username or Email already exists"):
            self.service.register("alice", "alice2@test.com", "pass123")

    def test_register_duplicate_email(self):
        self.service.register("alice", "alice@test.com", "pass123")
        with pytest.raises(ValueError, match="Username or Email already exists"):
            self.service.register("bob", "alice@test.com", "pass123")

    def test_register_invalid_email(self):
        with pytest.raises(ValueError, match="Invalid email format"):
            self.service.register("alice", "invalid-email", "pass123")

    def test_login_success(self):
        self.service.register("alice", "alice@test.com", "pass123")
        user = self.service.login("alice", "pass123")
        assert user.username == "alice"

    def test_login_wrong_password(self):
        self.service.register("alice", "alice@test.com", "pass123")
        with pytest.raises(ValueError, match="Incorrect password"):
            self.service.login("alice", "wrongpass")

    def test_login_nonexistent_user(self):
        with pytest.raises(ValueError, match="User not found"):
            self.service.login("nobody", "pass")


class TestProductService:
    def setup_method(self):
        self.service = ProductService()

    def test_add_product_success(self):
        p = self.service.add_product("Laptop", 1000.0, "Electronics", 10)
        assert p.product_id == 1
        assert p.name == "Laptop"
        assert p.stock == 10

    def test_add_product_negative_price(self):
        with pytest.raises(ValueError, match="Price and Stock must be non-negative"):
            self.service.add_product("Bad", -10.0, "Cat", 5)

    def test_get_product_not_found(self):
        assert self.service.get_product(999) is None

    def test_search_by_category(self):
        self.service.add_product("Laptop", 1000.0, "Electronics", 10)
        self.service.add_product("Shirt", 50.0, "Clothing", 20)
        
        electronics = self.service.search_products(category="Electronics")
        assert len(electronics) == 1
        assert electronics[0].name == "Laptop"

    def test_search_by_keyword(self):
        self.service.add_product("Gaming Laptop", 1000.0, "Electronics", 10)
        self.service.add_product("Office Laptop", 800.0, "Electronics", 5)
        
        laptops = self.service.search_products(keyword="Gaming")
        assert len(laptops) == 1
        assert laptops[0].name == "Gaming Laptop"

    def test_search_inactive_products_excluded(self):
        p = self.service.add_product("Old Item", 10.0, "Misc", 5)
        p.status = ProductStatus.INACTIVE
        
        results = self.service.search_products()
        assert len(results) == 0

    def test_update_stock(self):
        p = self.service.add_product("Item", 10.0, "Cat", 5)
        pid = p.product_id
        self.service.update_stock(pid, 5)
        updated_p = self.service.get_product(pid)
        assert updated_p.stock == 10


class TestCartService:
    def setup_method(self):
        self.prod_svc = ProductService()
        self.cart_svc = CartService(self.prod_svc)
        # Setup products
        self.p1 = self.prod_svc.add_product("Widget", 10.0, "Parts", 100)
        self.p2 = self.prod_svc.add_product("Gadget", 20.0, "Parts", 50)

    def test_add_to_cart_new_item(self):
        self.cart_svc.add_to_cart(1, self.p1.product_id, 2)
        items = self.cart_svc.get_cart_items(1)
        assert len(items) == 1
        assert items[0].quantity == 2

    def test_add_to_cart_existing_item_increases_qty(self):
        self.cart_svc.add_to_cart(1, self.p1.product_id, 2)
        self.cart_svc.add_to_cart(1, self.p1.product_id, 3)
        items = self.cart_svc.get_cart_items(1)
        assert items[0].quantity == 5

    def test_add_to_cart_insufficient_stock(self):
        self.cart_svc.add_to_cart(1, self.p1.product_id, 100)
        with pytest.raises(ValueError, match="Insufficient stock"):
            self.cart_svc.add_to_cart(1, self.p1.product_id, 1)

    def test_remove_from_cart(self):
        self.cart_svc.add_to_cart(1, self.p1.product_id, 2)
        self.cart_svc.remove_from_cart(1, self.p1.product_id)
        assert len(self.cart_svc.get_cart_items(1)) == 0

    def test_update_cart_quantity(self):
        self.cart_svc.add_to_cart(1, self.p1.product_id, 2)
        self.cart_svc.update_cart_quantity(1, self.p1.product_id, 5)
        items = self.cart_svc.get_cart_items(1)
        assert items[0].quantity == 5

    def test_update_cart_quantity_zero_removes_item(self):
        self.cart_svc.add_to_cart(1, self.p1.product_id, 2)
        self.cart_svc.update_cart_quantity(1, self.p1.product_id, 0)
        assert len(self.cart_svc.get_cart_items(1)) == 0

    def test_clear_cart(self):
        self.cart_svc.add_to_cart(1, self.p1.product_id, 2)
        self.cart_svc.clear_cart(1)
        assert len(self.cart_svc.get_cart_items(1)) == 0


class TestOrderService:
    def setup_method(self):
        self.user_svc = UserService()
        self.prod_svc = ProductService()
        self.cart_svc = CartService(self.prod_svc)
        self.order_svc = OrderService(self.user_svc, self.cart_svc, self.prod_svc)
        
        # Setup User
        self.user = self.user_svc.register("buyer", "buy@test.com", "pass")
        
        # Setup Products
        self.p1 = self.prod_svc.add_product("Book", 100.0, "Books", 10)
        self.p2 = self.prod_svc.add_product("Pen", 10.0, "Stationery", 20)

    def test_create_order_success(self):
        self.cart_svc.add_to_cart(self.user.user_id, self.p1.product_id, 2)
        order = self.order_svc.create_order(self.user.user_id)
        
        assert order.status.name == "PENDING"
        assert len(order.items) == 1
        # Normal tier, no discount. 2 * 100 = 200
        assert order.total_amount == 200.0
        
        # Check stock reduced
        assert self.p1.stock == 8
        
        # Check cart cleared
        assert len(self.cart_svc.get_cart_items(self.user.user_id)) == 0

    def test_create_order_empty_cart_raises(self):
        with pytest.raises(ValueError, match="Cart is empty"):
            self.order_svc.create_order(self.user.user_id)

    def test_pay_order_awards_points(self):
        self.cart_svc.add_to_cart(self.user.user_id, self.p1.product_id, 2)
        order = self.order_svc.create_order(self.user.user_id)
        
        self.order_svc.pay_order(order.order_id)
        
        assert order.status.name == "PAID"
        # Points = int(total_amount). 200 points.
        assert self.user.points == 200

    def test_pay_order_normal_tier_no_discount(self):
        self.cart_svc.add_to_cart(self.user.user_id, self.p1.product_id, 2)
        order = self.order_svc.create_order(self.user.user_id)
        self.order_svc.pay_order(order.order_id)
        # Base price 200. Normal tier 1.0. Total 200.
        assert order.total_amount == 200.0

    def test_pay_order_silver_tier_discount(self):
        self.user_svc.users[self.user.user_id].tier = Tier.SILVER
        self.cart_svc.add_to_cart(self.user.user_id, self.p1.product_id, 2)
        order = self.order_svc.create_order(self.user.user_id)
        self.order_svc.pay_order(order.order_id)
        # Base price 200. Silver tier 0.95. Total 190.0.
        assert order.total_amount == 190.0

    def test_cancel_order_restores_stock(self):
        self.cart_svc.add_to_cart(self.user.user_id, self.p1.product_id, 2)
        order = self.order_svc.create_order(self.user.user_id)
        self.order_svc.pay_order(order.order_id)
        
        initial_stock = self.p1.stock # Should be 8
        
        self.order_svc.cancel_order(order.order_id)
        
        restored_stock = self.p1.stock
        assert restored_stock == initial_stock + 2  # Back to 10
        assert order.status.name == "CANCELLED"

    def test_cancel_non_paid_order_raises(self):
        self.cart_svc.add_to_cart(self.user.user_id, self.p1.product_id, 2)
        order = self.order_svc.create_order(self.user.user_id)
        # Status is PENDING
        with pytest.raises(ValueError, match="Only paid orders can be cancelled"):
            self.order_svc.cancel_order(order.order_id)

    def test_sales_stats_basic(self):
        # Create two orders
        self.cart_svc.add_to_cart(self.user.user_id, self.p1.product_id, 2)
        order1 = self.order_svc.create_order(self.user.user_id)
        self.order_svc.pay_order(order1.order_id)
        
        # Add another user and product for variety
        user2 = self.user_svc.register("buyer2", "b2@test.com", "pass")
        self.cart_svc.add_to_cart(user2.user_id, self.p2.product_id, 1)
        order2 = self.order_svc.create_order(user2.user_id)
        self.order_svc.pay_order(order2.order_id)
        
        stats = self.order_svc.get_sales_stats()
        
        assert stats['total_orders'] == 2
        # Order 1: 200. Order 2: 10. Total 210.
        assert abs(stats['total_revenue'] - 210.0) < 0.01
        
        assert 'Book' in stats['by_product']
        assert stats['by_product']['Book']['quantity'] == 2
        assert stats['by_product']['Book']['revenue'] == 200.0
        
        assert 'Stationery' in stats['by_category']
        assert stats['by_category']['Stationery']['quantity'] == 1
        assert stats['by_category']['Stationery']['revenue'] == 10.0

    def test_sales_stats_filter_by_category(self):
        self.cart_svc.add_to_cart(self.user.user_id, self.p1.product_id, 2)
        order1 = self.order_svc.create_order(self.user.user_id)
        self.order_svc.pay_order(order1.order_id)
        
        user2 = self.user_svc.register("buyer2", "b2@test.com", "pass")
        self.cart_svc.add_to_cart(user2.user_id, self.p2.product_id, 1)
        order2 = self.order_svc.create_order(user2.user_id)
        self.order_svc.pay_order(order2.order_id)
        
        stats = self.order_svc.get_sales_stats(category="Books")
        
        assert stats['total_orders'] == 1
        assert stats['total_revenue'] == 200.0
        assert 'Book' in stats['by_product']
        assert 'Stationery' not in stats['by_category']