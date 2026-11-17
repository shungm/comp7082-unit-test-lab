"""Run using synthetic data only. Not executed on import."""
import cart
from repository import StoreRepository
from cart import ShoppingCart
from payments import FakePaymentGateway
from checkout import CheckoutService
from setup_db import initialize


def main():
    initialize()
    repo = StoreRepository()
    cart = ShoppingCart('demo-user', repo)
    print('Inventory from database before checkout:', repo.get_product('USB-01').stock)
    cart.add_item('USB-01', 1)
    cart.apply_discount('WELCOME10')
    cart.apply_discount('WELCOME10')
    result = CheckoutService(repo, FakePaymentGateway()).checkout(cart, 'TEST_TOKEN', 'demo-request-1')
    print('Order result:', result)
    print('Inventory from databaseafter checkout:', repo.get_product('USB-01').stock)
    print('Total amount charged:', result.total)


if __name__ == '__main__':
    main()
