"""Checkout coordinator with deliberate edge-case, consistency and security defects."""
from models import OrderResult


class CheckoutService:
    def __init__(self, repository, payment_gateway):
        self.repository = repository
        self.payment_gateway = payment_gateway

    def checkout(self, cart, payment_token, request_id):
        # Ensure request_id
        if not request_id:
            return OrderResult(None, 'rejected', 0)
        
        existing_order = self.repository.find_order_request_id(request_id)

        if existing_order:
            order_id, amount, status = existing_order   # Match SELECT column order in repository.py
            return OrderResult(order_id, status, amount) # Match OrderResult in model.py
        
        if len(cart.lines) == 0:
            return OrderResult(None, 'empty', 0)

        # Check cart items if in stock before order accepted
        for line in cart.lines:
            product = self.repository.get_product(line.sku)
            if product is None or product.stock < line.quantity:
                print(f'Product out of stock')
                return OrderResult(None, 'out_of_stock', 0)
        
        amount = cart.total()

        # Array checks cart for successful inventory reservations/deducts before processing
        cart_reservations = []

        for line in cart.lines:
            if self.repository.update_stock(line.sku, line.quantity):
                cart_reservations.append(line)
            else:
                for reserved in cart_reservations:
                    self.repository.restore_stock(reserved.sku, reserved.quantity)
                return OrderResult(None, 'out_of_stock', 0)

        try:
            response = self.payment_gateway.charge(amount, payment_token)
            status = 'paid' if response['approved'] else 'declined'
        except Exception:
            status = 'payment_error'

        if status == 'payment_error' or status == 'declined':
            for line in cart.lines:
                self.repository.restore_stock(line.sku, line.quantity)

        order_id = self.repository.save_order(cart.user_id, amount, status, request_id)

        if status == 'paid':
            cart.lines.clear()
            cart.discount_code = None
            cart.discounted_total = None
            cart.save()

        return OrderResult(order_id, status, amount)
