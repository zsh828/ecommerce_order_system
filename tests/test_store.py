import pytest
from src.models import User, Product, CartItem, Order, Tier, OrderStatus
from src.services import UserService, ProductService, CartService, OrderService


class TestStoreIntegration:
    """
    Integration tests for the store functionality.
    This file replaces the erroneous test_store.py that tried to import 'OrderItem'.
    The correct class for order items is 'CartItem'.
    """

    def setup_method(self):
        self.user_service = UserService()
        self.product_service = ProductService()
        self.cart_service = CartService(self.product_service)
        self.order_service = OrderService(self.user_service, self.cart_service, self.product_service)
        
        # Setup a user
        self.user = self.user_service.register("tester", "test@store.com", "password123")
        
        # Setup some products
        self.product1 = self.product_service.add_product("Python Book", 50.0, "Books", 10)
        self.product2 = self.product_service.add_product("Mouse", 25.0, "Electronics", 5)

    def test_full_purchase_flow(self):
        # 1. Add items to cart
        self.cart_service.add_to_cart(self.user.user_id, self.product1.product_id, 2)
        self.cart_service.add_to_cart(self.user.user_id, self.product2.product_id, 1)
        
        # 2. Verify cart contents
        cart_items = self.cart_service.get_cart_items(self.user.user_id)
        assert len(cart_items) == 2
        
        # 3. Create order
        order = self.order_service.create_order(self.user.user_id)
        assert order is not None
        assert order.status == OrderStatus.PENDING
        assert len(order.items) == 2
        
        # Calculate expected total (Normal tier, no discount)
        # 2 * 50 + 1 * 25 = 125
        assert order.total_amount == 125.0
        
        # 4. Pay for order
        paid_order = self.order_service.pay_order(order.order_id)
        assert paid_order.status == OrderStatus.PAID
        
        # 5. Verify points awarded
        assert self.user.points == 125
        
        # 6. Verify stock reduction
        assert self.product1.stock == 8
        assert self.product2.stock == 4
        
        # 7. Verify cart is cleared
        assert len(self.cart_service.get_cart_items(self.user.user_id)) == 0

    def test_cancel_order_flow(self):
        # 1. Create and pay for an order
        self.cart_service.add_to_cart(self.user.user_id, self.product1.product_id, 1)
        order = self.order_service.create_order(self.user.user_id)
        self.order_service.pay_order(order.order_id)
        
        initial_stock = self.product1.stock
        
        # 2. Cancel order
        cancelled_order = self.order_service.cancel_order(order.order_id)
        assert cancelled_order.status == OrderStatus.CANCELLED
        
        # 3. Verify stock restoration
        assert self.product1.stock == initial_stock + 1

    def test_import_correctness(self):
        """
        Explicitly test that the imports work correctly to prevent regression of the CI error.
        """
        from src.models import CartItem
        # Ensure CartItem can be instantiated
        product = Product(1, "Test", 10.0, "Cat", 10)
        item = CartItem(product, 1)
        assert item.quantity == 1
        assert item.total_price == 10.0