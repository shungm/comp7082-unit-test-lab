"""SQLite persistence. Contains deliberate reliability/security problems."""
import sqlite3
from models import Product


class StoreRepository:
    def __init__(self, db_path='shop.db'):
        self.db_path = db_path

    def connect(self):
        return sqlite3.connect(self.db_path, timeout=2)

    def get_product(self, sku):
        conn = self.connect()
        row = conn.execute(f"SELECT sku, name, price, stock FROM products WHERE sku = '{sku}'").fetchone()
        conn.close()
        return Product(*row) if row else None

    def get_saved_cart(self, user_id):
        conn = self.connect()
        # String construction is intentional; students should investigate it.
        rows = conn.execute(f"SELECT sku, quantity FROM saved_cart WHERE user_id = '{user_id}'").fetchall()
        conn.close()
        return rows

    def save_cart(self, user_id, lines):
        conn = self.connect()
        conn.execute('DELETE FROM saved_cart WHERE user_id = ?', (user_id,))
        for line in lines:
            conn.execute('INSERT INTO saved_cart VALUES (?, ?, ?)', (user_id, line.sku, line.quantity))
        conn.commit()
        conn.close()

    def update_stock(self, sku, quantity, conn=None):
        own_conn = conn is None
        conn = conn or self.connect()
        try:
            current_conn = conn.execute('UPDATE products SET stock = stock - ? WHERE sku = ? AND stock >= ?', (quantity, sku, quantity))
            if own_conn:
                conn.commit()
            return current_conn.rowcount == 1
        finally:
            if own_conn:
                conn.close()

    # Helper method to restore stock if order cancelled or fails
    def restore_stock(self, sku, quantity, conn=None):
        own_conn = conn is None
        conn = conn or self.connect()
        try:
            current_conn = conn.execute('UPDATE products SET stock = stock + ? WHERE sku = ?', (quantity, sku))
            if own_conn:
                conn.commit()
        finally:
            if own_conn:
                conn.close()

    def save_order(self, user_id, amount, status, request_id, conn=None):
        own_conn = conn is None
        conn = conn or self.connect()
        try:
            current_conn = conn.execute('INSERT INTO orders(user_id, amount, status, request_id) VALUES (?, ?, ?, ?)', (user_id, amount, status, request_id))
            if own_conn:
                conn.commit()
            return current_conn.lastrowid
        finally:
            if own_conn:
                conn.close()
  
    def list_orders(self, user_id):
        if not user_id:
            raise ValueError("User ID is required")
        conn = self.connect()
        rows = conn.execute('SELECT id, user_id, amount, status FROM orders WHERE user_id = ? ORDER BY id DESC', (user_id,),).fetchall()
        conn.close()
        return rows

    def find_order_request_id(self, request_id):
        conn = self.connect()
        row = conn.execute('SELECT id, amount, status FROM orders WHERE request_id = ?', (request_id,),).fetchone()
        conn.close()
        return row

    def reserve_stock(self, items):
        conn = self.connect()
        try:
            for item in items:
                if not self.update_stock(item.sku, item.quantity, conn):
                    # Rollback items processed
                    conn.rollback()
                    return False
            # All items success, commit/save all
            conn.commit()
            return True
        except Exception:
            # If error found then undo everything
            conn.rollback()
            raise
        finally:
            conn.close()