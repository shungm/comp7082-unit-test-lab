"""Run using synthetic data only. Not executed on import."""
import cart
from repository import StoreRepository
from cart import ShoppingCart
from payments import FakePaymentGateway
from checkout import CheckoutService
from setup_db import initialize

class FailingGateway(FakePaymentGateway):
    def charge(self, amount, payment_token):
        raise TimeoutError("Testing Gateway timeout")
    
def main():
    initialize()
    repo = StoreRepository()
    cart = ShoppingCart('demo-user', repo)
    print('Inventory from database before checkout:', repo.get_product('USB-01').stock)

    #print('Add qty 0 (expect False):', cart.add_item('USB-01', 0))
    #print('Add qty -1 (expect False):', cart.add_item('USB-01', -1))
    #print('Add 1 valid USB-01 (expect True):', cart.add_item('USB-01', 1))

    #cart.apply_discount('WELCOME10')
    #cart.apply_discount('WELCOME10')
    #print('Total after discounts:', cart.total())

    #service = CheckoutService(repo, FakePaymentGateway(should_approve=True))
    #result = service.checkout(cart, 'TEST_TOKEN', 'demo-request-1')
    #duplicate_result = service.checkout(cart, 'TEST_TOKEN', 'demo-request-1')
    #print('Order result:', result)
    #print('Duplicate request_id result:', duplicate_result)
    #print('Inventory from database after checkout:', repo.get_product('USB-01').stock)
    #print('Total amount charged:', result.total)


    cart_declined = ShoppingCart('demo-user', repo)
    cart_declined.add_item('MOU-01', 2)
    before_declined = repo.get_product('MOU-01').stock
    declined_service = CheckoutService(repo, FakePaymentGateway(should_approve=False))
    declined_res = declined_service.checkout(cart_declined, 'TEST_TOKEN', 'demo-declined-1')
    print('Declined result:', declined_res, '| MOU-01 stock before/after:', before_declined, repo.get_product('MOU-01').stock)


if __name__ == '__main__':
    main()
