from src.models import User, Product, Order, OrderItem


class Store:
    def __init__(self):
        self.users: dict[str, User] = {}
        self.products: dict[str, Product] = {}
        self.orders: dict[str, Order] = {}
        self.carts: dict[str, list[OrderItem]] = {}  # user_id -> list of OrderItems
        self.next_user_id = 1
        self.next_product_id = 1
        self.next_order_id = 1

    def register_user(self, username: str, email: str, password: str) -> User:
        if username in self.users or any(u.email == email for u in self.users.values()):
            raise ValueError("Username or Email already exists")
        
        user_id = f"U{self.next_user_id}"
        self.next_user_id += 1
        user = User(username, email, password)
        self.users[user_id] = user
        self.carts[user_id] = []
        return user

    def login_user(self, username: str, password: str) -> User:
        for user in self.users.values():
            if user.username == username and user.check_password(password):
                return user
        raise ValueError("Invalid credentials")

    def add_product(self, name: str, category: str, price: float, stock: int) -> Product:
        product_id = f"P{self.next_product_id}"
        self.next_product_id += 1
        product = Product(product_id, name, category, price, stock)
        self.products[product_id] = product
        return product

    def get_products(self, category: str = None) -> list[Product]:
        if category:
            return [p for p in self.products.values() if p.category == category]
        return list(self.products.values())

    def get_product_by_id(self, product_id: str) -> Product:
        if product_id not in self.products:
            raise ValueError("Product not found")
        return self.products[product_id]

    def add_to_cart(self, user: User, product_id: str, quantity: int):
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        product = self.get_product_by_id(product_id)
        
        # Check stock availability
        current_cart_qty = sum(item.quantity for item in self.carts[user.username] if item.product.product_id == product_id)
        if current_cart_qty + quantity > product.stock:
            raise ValueError("Insufficient stock")

        # Find existing item in cart
        existing_item = next((item for item in self.carts[user.username] if item.product.product_id == product_id), None)
        if existing_item:
            existing_item.quantity += quantity
        else:
            self.carts[user.username].append(OrderItem(product, quantity))

    def remove_from_cart(self, user: User, product_id: str):
        original_len = len(self.carts[user.username])
        self.carts[user.username] = [item for item in self.carts[user.username] if item.product.product_id != product_id]
        if len(self.carts[user.username]) == original_len:
            raise ValueError("Item not in cart")

    def update_cart_quantity(self, user: User, product_id: str, new_quantity: int):
        if new_quantity <= 0:
            self.remove_from_cart(user, product_id)
            return

        item = next((item for item in self.carts[user.username] if item.product.product_id == product_id), None)
        if not item:
            raise ValueError("Item not in cart")

        product = item.product
        # Check total stock including other items if necessary, but simplified here to just this item's limit vs stock
        # Strictly speaking, we should check if (new_quantity) <= product.stock. 
        # However, usually cart quantity shouldn't exceed available stock.
        if new_quantity > product.stock:
            raise ValueError("Insufficient stock")
        
        item.quantity = new_quantity

    def create_order(self, user: User) -> Order:
        cart_items = self.carts.get(user.username, [])
        if not cart_items:
            raise ValueError("Cart is empty")

        # Validate stock one last time before creating order
        for item in cart_items:
            if item.quantity > item.product.stock:
                raise ValueError(f"Insufficient stock for {item.product.name}")

        order_id = f"O{self.next_order_id}"
        self.next_order_id += 1
        
        # Create deep copy of items to avoid reference issues if stock changes later? 
        # In this simple model, OrderItem holds reference to Product object.
        # We need to ensure the order captures the state at creation.
        # Since Product object is mutable, we rely on the fact that we deduct stock immediately upon payment/cancellation logic handles it.
        # But for Order creation, status is pending. Stock is deducted on PAY.
        
        order = Order(order_id, user, cart_items)
        self.orders[order_id] = order
        
        # Clear cart
        self.carts[user.username] = []
        
        return order

    def cancel_order(self, user: User, order_id: str) -> Order:
        order = self.orders.get(order_id)
        if not order:
            raise ValueError("Order not found")
        if order.user.username != user.username:
            raise ValueError("Unauthorized access")
        
        order.cancel()
        return order

    def pay_order(self, user: User, order_id: str) -> Order:
        order = self.orders.get(order_id)
        if not order:
            raise ValueError("Order not found")
        if order.user.username != user.username:
            raise ValueError("Unauthorized access")
        
        order.pay()
        return order

    def get_sales_stats(self, start_date=None, end_date=None) -> dict:
        """
        Returns sales statistics.
        Structure: {
            'total_revenue': float,
            'by_category': {category: revenue},
            'by_product': {product_name: revenue},
            'orders_count': int
        }
        """
        filtered_orders = []
        for order in self.orders.values():
            if order.status != "paid":
                continue
            
            if start_date and order.created_at < start_date:
                continue
            if end_date and order.created_at > end_date:
                continue
                
            filtered_orders.append(order)

        total_revenue = sum(o.total_amount for o in filtered_orders)
        by_category = {}
        by_product = {}
        
        for order in filtered_orders:
            for item in order.items:
                cat = item.product.category
                prod_name = item.product.name
                subtotal = item.get_subtotal()
                
                # Note: The order total includes discounts. 
                # For accurate revenue reporting, we usually report actual money received.
                # However, breakdowns are tricky with discounts. 
                # Simple approach: Distribute discount proportionally or just use subtotal.
                # Let's use the discounted contribution.
                # To keep it simple and consistent with `total_amount`, let's calculate ratio.
                
                order_total = order.total_amount
                order_subtotal_raw = sum(i.get_subtotal() for i in order.items)
                
                if order_subtotal_raw > 0:
                    ratio = item.get_subtotal() / order_subtotal_raw
                    contribution = order_total * ratio
                else:
                    contribution = 0

                by_category[cat] = by_category.get(cat, 0) + contribution
                by_product[prod_name] = by_product.get(prod_name, 0) + contribution

        return {
            'total_revenue': total_revenue,
            'by_category': by_category,
            'by_product': by_product,
            'orders_count': len(filtered_orders)
        }