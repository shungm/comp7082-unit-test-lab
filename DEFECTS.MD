cart.py
1. In ShoppingCart class:
    - No check for quantity if value is 0 => "No stock available" or negative numbers
        - User still gets charged and checkout still successful when testing for these values
2. In apply_discount method:
    - No check against stacking the same coupon multiple times



checkout.py
3. In checkout method:
    - Stock permanently gets removed once added despite removing item from cart right after

4. In checkout method:
    - If order/adding item when there is no stock or if order number greater than available stock. Order successfully added instead of being rejected