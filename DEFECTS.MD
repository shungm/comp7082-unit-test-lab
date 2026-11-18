
cart.py

1. **In ShoppingCart class:**

	- No check for quantity if value is 0 => "No stock available" or negative numbers (Add check for non-integer values) (Lines 	15-18)

	- User still gets charged and checkout still successful when testing for these values

2. **In apply_discount method:**

	- No check against stacking the same coupon multiple times

3. **In add_item method:**

	- When adding more of the same item, the numbers added can exceed what is in the inventory - items in existing cart not considered for the total amount of stock. (Line 18 - Line 23)

  

checkout.py

4. **In checkout method:**

	- Stock permanently gets removed once added despite removing item from cart right after, checkout failures(Line 22, Line 23) - Inventory decrement before payment/checkout succeeds

5. **In checkout method:**
	
	- If order/adding item when there is no stock or if order number greater than available stock. Order successfully added instead of being rejected (Line 15 - Line 20) - No order rejection

6. **In checkout method:**

	- Duplicate transactions can occur if multiple checkout calls of same order (line 29)

  

repository.py

7. **In update_stock:**

	- Nothing to stop inventory from becoming negative if user adds more items in cart more than what's in inventory (Line 36)

8. **In list_orders:**

	- user_id for an order is not specified so orders of all users is shown when list order called (Line 51)
