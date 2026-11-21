import pytest
import threading

from cart import ShoppingCart
from checkout import CheckoutService
from payments import FakePaymentGateway
from repository import StoreRepository
from setup_db import initialize


class FailingPaymentGateway(FakePaymentGateway):
    def charge(self, amount, payment_token):
        raise TimeoutError()


# Setup function that is automatically passed to test functions
@pytest.fixture
def test_product(tmp_path):
    db = tmp_path / 'test.db'
    initialize(str(db))
    return StoreRepository(str(db))


def test_successful_checkout_deducts_stock(test_product):
    cart = ShoppingCart("user-1", test_product)
    initial_stock = test_product.get_product("MOU-01").stock

    assert cart.add_item("MOU-01", 3) is True

    gateway = FakePaymentGateway(should_approve=True)
    service = CheckoutService(test_product, gateway)

    result = service.checkout(cart, "TEST_TOKEN", "success-1")

    assert result.status == "paid"
    assert test_product.get_product("MOU-01").stock == initial_stock - 3
    assert cart.lines == []


def test_cart_add_same_item_not_exceed_stock(test_product):
    cart = ShoppingCart("user-1", test_product)
    assert cart.add_item("LAP-01", 3) is True
    assert cart.add_item("LAP-01", 3) is False   
    assert cart.lines[0].quantity == 3


def test_add_and_remove_item_rejecting_invalid_quantities(test_product):
    cart = ShoppingCart("user-1", test_product)

    # Zero, negative, boolean, and non-integer quantities should be rejected
    assert cart.add_item("MOU-01", 0) is False
    assert cart.add_item("MOU-01", -2) is False
    assert cart.add_item("MOU-01", True) is False
    assert cart.add_item("MOU-01", 1.5) is False
    assert cart.lines == []

    # Add 3 valid items, then test invalid remove quantities
    assert cart.add_item("MOU-01", 3) is True
    assert cart.remove_item("MOU-01", 0) is False
    assert cart.remove_item("MOU-01", -1) is False
    assert cart.lines[0].quantity == 3


def test_add_up_to_exact_stock_then_one_more(test_product):
    cart = ShoppingCart("u", test_product)
    assert cart.add_item("LAP-01", 3) is True
    assert cart.add_item("LAP-01", 2) is True
    assert cart.add_item("LAP-01", 1) is False


def test_update_stock_never_goes_negative(test_product):
    assert test_product.update_stock("LAP-01", 6) is False
    assert test_product.get_product("LAP-01").stock == 5
    assert test_product.update_stock("LAP-01", 5) is True
    assert test_product.update_stock("LAP-01", 1) is False
    assert test_product.get_product("LAP-01").stock == 0


def test_same_coupon_twice(test_product):
    cart = ShoppingCart("u", test_product)
    cart.add_item("MOU-01", 2)
    cart.apply_discount("WELCOME10")
    cart.apply_discount("WELCOME10")
    assert cart.total() == pytest.approx(59.90 * 0.9) 


def test_discount_not_stacking(test_product):
    cart = ShoppingCart("user-1", test_product)
    assert cart.add_item("MOU-01", 2) is True

    # Applying a second coupon should replace instead of stacking
    assert cart.apply_discount("WELCOME10") is True
    assert cart.total() == pytest.approx(59.90 * 0.9)

    assert cart.apply_discount("STUDENT20") is True
    assert cart.total() == pytest.approx(59.90 * 0.8)

    # Adding another item should recalculate from the updated subtotal
    assert cart.add_item("MOU-01", 1) is True
    assert cart.total() == pytest.approx(89.85 * 0.8)


def test_coupon_not_totalling_negative(test_product):
    cart = ShoppingCart("user-1", test_product)
    assert cart.add_item("USB-01", 1) is True
    assert cart.apply_discount("SAVE15") is True
    assert cart.total() == 0


def test_checkout_rejecting_not_enough_stock(test_product):
    cart = ShoppingCart("user-1", test_product)

    # Overstock test
    assert cart.add_item("LAP-01", 5) is True
    cart.lines[0].quantity = 10

    gateway = FakePaymentGateway(should_approve=True)
    service = CheckoutService(test_product, gateway)

    result = service.checkout(cart, "TEST_TOKEN", "stock-1")

    assert result.status == "out_of_stock"
    assert result.order_id is None
    assert gateway.calls == [] 
    assert test_product.get_product("LAP-01").stock == 5  # Stock unchanged
    assert len(cart.lines) == 1  # Cart still has item


def test_checkout_unchanged_inventory_when_checkout_fails(test_product):
    cart = ShoppingCart("user-1", test_product)
    assert cart.add_item("MOU-01", 4) is True

    gateway = FakePaymentGateway(should_approve=False)
    service = CheckoutService(test_product, gateway)

    result = service.checkout(cart, "TEST_TOKEN", "fail-1")

    # Stock should stay as 20 with no changes to cart (Order declined)
    assert result.status == "declined"
    assert test_product.get_product("MOU-01").stock == 20
    assert len(cart.lines) == 1
    assert cart.lines[0].quantity == 4
    assert test_product.list_orders("user-1")[0][3] == "declined"


def test_checkout_no_duplicate_charges(test_product):
    cart = ShoppingCart("user-1", test_product)
    assert cart.add_item("USB-01", 2) is True

    gateway = FakePaymentGateway(should_approve=True)
    service = CheckoutService(test_product, gateway)

    first_result = service.checkout(cart, "TEST_TOKEN", "dup-1")
    second_result = service.checkout(cart, "TEST_TOKEN", "dup-1")

    assert first_result.order_id is not None
    assert second_result.order_id == first_result.order_id
    assert second_result.total == first_result.total

    # Make sure only charged once
    assert len(gateway.calls) == 1
    # Make sure only one row svaed
    assert len(test_product.list_orders("user-1")) == 1


def test_checkout_rejects_missing_request_id(test_product):
    cart = ShoppingCart("user-1", test_product)
    cart.add_item("MOU-01", 1)
    gateway = FakePaymentGateway(should_approve=True)
    result = CheckoutService(test_product, gateway).checkout(cart, "TEST_TOKEN", None)
    assert result.status == "rejected"
    assert gateway.calls == []


def test_list_orders_by_user_id(test_product):
    # Test orders for 2 users: ALice and Bob
    test_product.save_order("Alice", 59.90, "paid", "alice-1")
    test_product.save_order("Bob", 999.99, "paid", "bob-1")
    test_product.save_order("Alice", 9.99, "declined", "alice-2")

    alice_orders = test_product.list_orders("Alice")
    bob_orders = test_product.list_orders("Bob")

    # Alice should only see her orders
    assert len(alice_orders) == 2
    assert all(row[1] == "Alice" for row in alice_orders)

    # Bob should only see his order
    assert len(bob_orders) == 1
    assert bob_orders[0][1] == "Bob"


def test_list_order_missing_user_id(test_product):
    test_product.save_order("Alice", 50.99, "paid", "alice-1")

    with pytest.raises(ValueError, match = "User ID is required"):
        test_product.list_orders("")

    with pytest.raises(ValueError, match = "User ID is required"):
        test_product.list_orders(None)


def test_checkout_restores_stock_on_payment_error(test_product):
    cart = ShoppingCart("user-1", test_product)
    initial_stock = test_product.get_product("MOU-01").stock

    assert cart.add_item("MOU-01", 3) is True
    cart.save()

    gateway = FailingPaymentGateway()
    service = CheckoutService(test_product, gateway)

    result = service.checkout(cart, "TEST_TOKEN", "error-1")

    assert result.status == "payment_error"
    assert test_product.get_product("MOU-01").stock == initial_stock
    assert len(cart.lines) == 1
    assert cart.lines[0].quantity == 3
    assert test_product.list_orders("user-1")[0][3] == "payment_error"

def test_reserve_stock_rollingback_when_no_stock(test_product):
    # First order
    cart = ShoppingCart("user-1", test_product)
    assert cart.add_item("MOU-01", 3) is True
    assert cart.add_item("LAP-01", 5) is True

    # Second order buying LAP-01
    assert test_product.update_stock("LAP-01", 2) is True

    assert test_product.reserve_stock(cart.lines) is False
    assert test_product.get_product("MOU-01").stock == 20
    assert test_product.get_product("LAP-01").stock == 3

def test_get_product_handling_sql_injection(test_product):
    product = test_product.get_product("MOU-01")
    assert product is not None
    assert product.sku == "MOU-01"

    # SQL-injection give error
    injection = "' OR '1'='1"
    assert test_product.get_product(injection) is None


def test_get_saved_cart_handling_sql_injection(test_product):
    # Save and verify user-1 cart
    cart = ShoppingCart("user-1", test_product)
    assert cart.add_item("MOU-01", 2) is True
    cart.save()

    saved = test_product.get_saved_cart("user-1")
    assert saved == [("MOU-01", 2)]

    # user-1 cart should not be visible to user-2
    assert test_product.get_saved_cart("user-2") == []

    # SQL-injection give error
    assert test_product.get_saved_cart("' OR '1'='1") == []


def test_concurrent_reserve_stock_prevents_overselling(test_product):
    # Starts with 5 in stock; two both threads try to get 4
    cart_a = ShoppingCart("user-a", test_product)
    cart_b = ShoppingCart("user-b", test_product)
    assert cart_a.add_item("LAP-01", 4) is True
    assert cart_b.add_item("LAP-01", 4) is True

    barrier = threading.Barrier(2)
    results = []
    lock = threading.Lock()

    def worker(lines):
        barrier.wait()
        reserved = test_product.reserve_stock(lines)
        with lock:
            results.append(reserved)

    t1 = threading.Thread(target=worker, args=(cart_a.lines,))
    t2 = threading.Thread(target=worker, args=(cart_b.lines,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Only one reservation should save
    assert sorted(results) == [False, True]
    assert test_product.get_product("LAP-01").stock == 1


def test_concurrent_checkouts_prevent_overselling(test_product):
    # Two separate carts
    barrier = threading.Barrier(2)
    checkout_results = []
    lock = threading.Lock()

    def run_checkout(user_id, request_id):
        cart = ShoppingCart(user_id, test_product)
        assert cart.add_item("LAP-01", 4) is True
        gateway = FakePaymentGateway(should_approve=True)
        service = CheckoutService(test_product, gateway)

        barrier.wait()
        res = service.checkout(cart, "TEST_TOKEN", request_id)
        with lock:
            checkout_results.append((user_id, res))

    t1 = threading.Thread(target=run_checkout, args=("user-1", "req-conc-1"))
    t2 = threading.Thread(target=run_checkout, args=("user-2", "req-conc-2"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    statuses = sorted(res.status for _, res in checkout_results)
    assert statuses == ["out_of_stock", "paid"]
    assert test_product.get_product("LAP-01").stock == 1

    # Only successful payment should save order
    assert len(test_product.list_orders("user-1")) + len(test_product.list_orders("user-2")) == 1