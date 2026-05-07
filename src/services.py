import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models import User, Product, CartItem, Order, Tier, OrderStatus, ProductStatus, validate_email, hash_password, verify_password


class UserService:
    def __init__(self):
        self.users = {}
        self.next_user_id = 1

    def register(self, username: str, email: str, password: str) -> User:
        if not validate_email(email):
            raise ValueError("Invalid email format")
        
        # Check for duplicate username by iterating through values
        if any(u.username == username for u in self.users.values()):
            raise ValueError("Username or Email already exists")
            
        if any(u.email == email for u in self.users.values()):
            raise ValueError("Username or Email already exists")

        pw_hash, salt = hash_password(password)
        user = User(
            user_id=self.next_user_id,
            username=username,
            email=email,
            password_hash=pw_hash,
            salt=salt,
            tier=Tier.NORMAL,
            points=0
        )
        self.users[user.user_id] = user
        self.next_user_id += 1
        return user

    def login(self, username: str, password: str) -> User:
        user = next((u for u in self.users.values() if u.username == username), None)
        if not user:
            raise ValueError("User not found")
        
        if not verify_password(password, user.password_hash, user.salt):
            raise ValueError("Incorrect password")
        
        return user


class ProductService:
    def __init__(self):
        self.products = {}
        self.next_product_id = 1

    def add_product(self, name: str, price: float, category: str, stock: int) -> Product:
        if price < 0 or stock < 0:
            raise ValueError("Price and Stock must be non-negative")
        
        product = Product(
            product_id=self.next_product_id,
            name=name,
            price=price,
            category=category,
            stock=stock
        )
        self.products[product.product_id] = product
        self.next_product_id += 1
        return product

    def get_product(self, product_id: int) -> Product:
        return self.products.get(product_id)

    def search_products(self, category: str = None, keyword: str = None) -> list:
        results = []
        for p in self.products.values():
            if p.status != ProductStatus.ACTIVE:
                continue
            
            match_category = category is None or p.category == category
            match_keyword = keyword is None or keyword.lower() in p.name.lower()
            
            if match_category and match_keyword:
                results.append(p)
        return results

    def update_stock(self, product_id: int, quantity_change: int) -> bool:
        product = self.products.get(product_id)
        if not product:
            return False
        product.update_stock(quantity_change)
        return True


class CartService:
    def __init__(self, product_service: ProductService):
        self.carts = {}  # user_id -> {product_id: CartItem}
        self.product_service = product_service

    def add_to_cart(self, user_id: int, product_id: int, quantity: int):
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        product = self.product_service.get_product(product_id)
        if not product:
            raise ValueError("Product not found")
        
        if not product.check_availability(quantity):
            raise ValueError("Insufficient stock")

        if user_id not in self.carts:
            self.carts[user_id] = {}
        
        if product_id in self.carts[user_id]:
            current_item = self.carts[user_id][product_id]
            if not product.check_availability(current_item.quantity + quantity):
                raise ValueError("Insufficient stock for combined quantity")
            current_item.quantity += quantity
        else:
            self.carts[user_id][product_id] = CartItem(product, quantity)

    def remove_from_cart(self, user_id: int, product_id: int):
        if user_id in self.carts and product_id in self.carts[user_id]:
            del self.carts[user_id][product_id]
            if not self.carts[user_id]:
                del self.carts[user_id]

    def update_cart_quantity(self, user_id: int, product_id: int, quantity: int):
        if quantity <= 0:
            self.remove_from_cart(user_id, product_id)
            return
        
        if user_id not in self.carts or product_id not in self.carts[user_id]:
            raise ValueError("Item not in cart")
        
        product = self.product_service.get_product(product_id)
        if not product.check_availability(quantity):
            raise ValueError("Insufficient stock")
        
        self.carts[user_id][product_id].quantity = quantity

    def get_cart_items(self, user_id: int) -> list:
        return list(self.carts.get(user_id, {}).values())

    def clear_cart(self, user_id: int):
        if user_id in self.carts:
            del self.carts[user_id]


class OrderService:
    def __init__(self, user_service: UserService, cart_service: CartService, product_service: ProductService):
        self.orders = {}
        self.next_order_id = 1
        self.user_service = user_service
        self.cart_service = cart_service
        self.product_service = product_service

    def create_order(self, user_id: int) -> Order:
        cart_items = self.cart_service.get_cart_items(user_id)
        if not cart_items:
            raise ValueError("Cart is empty")
        
        # Final stock check before creating order
        for item in cart_items:
            if not item.product.check_availability(item.quantity):
                raise ValueError(f"Stock insufficient for {item.product.name}")
        
        # Deduct stock
        for item in cart_items:
            item.product.update_stock(-item.quantity)
        
        user = self.user_service.users.get(user_id)
        if not user:
            raise ValueError("User not found")
            
        order = Order(
            order_id=self.next_order_id,
            user=user,
            items=cart_items
        )
        self.orders[order.order_id] = order
        self.next_order_id += 1
        
        # Clear cart
        self.cart_service.clear_cart(user_id)
        
        return order

    def pay_order(self, order_id: int) -> Order:
        order = self.orders.get(order_id)
        if not order:
            raise ValueError("Order not found")
        if order.status != OrderStatus.PENDING:
            raise ValueError("Order cannot be paid in current status")
        
        order.status = OrderStatus.PAID
        
        # Award points
        order.user.add_points(int(order.total_amount))
        
        return order

    def cancel_order(self, order_id: int) -> Order:
        order = self.orders.get(order_id)
        if not order:
            raise ValueError("Order not found")
        if order.status != OrderStatus.PAID:
            raise ValueError("Only paid orders can be cancelled")
        
        # Restore stock
        for item in order.items:
            item.product.update_stock(item.quantity)
            
        order.cancel()
        return order

    def get_order(self, order_id: int) -> Order:
        return self.orders.get(order_id)

    def get_sales_stats(self, start_date=None, end_date=None, category=None) -> dict:
        stats = {
            'total_revenue': 0.0,
            'total_orders': 0,
            'by_product': {},
            'by_category': {}
        }
        
        for order in self.orders.values():
            if order.status != OrderStatus.PAID:
                continue
            
            if start_date and order.created_at < start_date:
                continue
            if end_date and order.created_at > end_date:
                continue
                
            # If filtering by category, check if the order contains any products in that category
            if category:
                has_matching_product = False
                for item in order.items:
                    if item.product.category == category:
                        has_matching_product = True
                        break
                if not has_matching_product:
                    continue

            stats['total_revenue'] += order.total_amount
            stats['total_orders'] += 1
            
            for item in order.items:
                prod_name = item.product.name
                cat = item.product.category
                
                if category and cat != category:
                    continue
                    
                if prod_name not in stats['by_product']:
                    stats['by_product'][prod_name] = {'quantity': 0, 'revenue': 0.0}
                
                stats['by_product'][prod_name]['quantity'] += item.quantity
                stats['by_product'][prod_name]['revenue'] += item.total_price
                
                if cat not in stats['by_category']:
                    stats['by_category'][cat] = {'quantity': 0, 'revenue': 0.0}
                    
                stats['by_category'][cat]['quantity'] += item.quantity
                stats['by_category'][cat]['revenue'] += item.total_price
                
        return stats