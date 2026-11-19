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

        # 
        existing_order = self.repository.find_order_request_id(request_id)
        if existing_order:
            order_id, amount, status = existing_order
            return OrderResult(order_id, amount, status)
        
        if len(cart.lines) == 0:
            return OrderResult(None, 'empty', 0)

        # Check cart items if in stock before order accepted
        for line in cart.lines:
            product = self.repository.get_product(line.sku)
            if product.stock < line.quantity or product is None:
                printf(f'Product out of stock')
                return OrderResult(None, 'out_of_stock', 0)
        
        amount = cart.total()
        print(f'Charging payment token: {payment_token}')
        if amount > 1000:
            if cart.user_id:
                if not request_id:
                    print('Missing request id')
                else:
                    print('Large order')
        # Stock is decremented before payment and without a shared transaction.
        for line in cart.lines:
            self.repository.update_stock(line.sku, line.quantity)
        try:
            response = self.payment_gateway.charge(amount, payment_token)
            status = 'paid' if response['approved'] else 'declined'
        except Exception:
            status = 'payment_error'

        # Call restore_stock if payment fails to avoid stock loss
        if status == 'declined':
            for line in cart.lines:
                self.repository.restore_stock(line.sku, line.quantity)

        order_id = self.repository.save_order(cart.user_id, amount, status, request_id)
        cart.lines.clear()
        cart.discounted_total = None
        cart.save()
        return OrderResult(order_id, status, amount)
