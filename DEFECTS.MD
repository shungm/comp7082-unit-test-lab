
cart.py

1. **In add_item and remove_item methods:**

	- No check for quantity if value is 0 => "No stock available" or negative numbers (Add check for non-integer values) (Lines 15-18)
	- When removing a negative amount of item (ex: quantity = -3), quantity increases	(Lines 21)

	- User still gets charged and checkout still successful when testing for these values

	**Fix**: Add check to reject non-positive values (n <= 0) and non-integers (ex: No such thing as buying half a laptop)

2. **In apply_discount method:**

	- No check against stacking the same coupon multiple times
	
	**Fix**: In the apply_discount method, use "self.subtotal" instead of "self.total()" for the discount calculation because "self.total()" includes discount already. Also add a helper method to reapply discount code to recalculate the discounted total if changes are made to cart.

3. **In add_item method**

	- When adding more of the same item, the numbers added can exceed what is in the inventory - items in existing cart not considered for the total amount of stock. (Line 18 - Line 23)

	**Fix**: Add a check to see if the stock in the cart exceeds the amount in inventory in 

  

checkout.py + repository.py

4. **In checkout method:**

	- Stock permanently gets removed once added despite removing item from cart right after, checkout failures(Line 22, Line 23) - Inventory decrement before payment/checkout succeeds

	**Fix:** Add method to reserve and restore stock back if order in repository.py and call the method from checkout.py when payment cancelled/declines


checkout.py

5. **In checkout method:**
	
	- If order/adding item when there is no stock or if order number greater than available stock. Order successfully added instead of being rejected (Line 15 - Line 20) - No order rejection

	**Fix:** Add check to checkout to check current product stock before fulfilling order to catch zero stock and over ordering product
	

checkout.py + repository.py

6. **In checkout method:**

	- Duplicate transactions can occur if multiple checkout calls of same order (line 29)

	**Fix:** Add method in repository.py to search for existing order by request_id before checking out. In checkout method, add a check to see if existing order already exists to prevent same cart from being checked out/processed more than once.

7. **In checkout method:**
	- Stock decremented before payment -> stock disappearing if checkout fails or cancelled

	**Fix:** Add a check to make sure stock decrements only if payment or order is approved

  

repository.py

8. **In update_stock:**

	- Nothing to stop inventory from becoming negative if user adds more items in cart more than what's in inventory (Line 36)
	**Fix:** Add condition to only subtract when there is enough inventory to update_stock method

9. **In list_orders:**

	- user_id for an order is not specified so orders of all users is shown when list order called (Line 51)

	**Fix:** Add user_id in the query in list_orders method
