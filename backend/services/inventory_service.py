from backend.database import get_db

class InventoryService:
    @staticmethod
    def check_availability(variant_id, requested_qty=1, conn=None):
        """Checks if a variant has sufficient available stock."""
        def _check(c):
            row = c.execute("""
                SELECT id, stock_quantity, low_stock_threshold
                FROM product_variants WHERE id = ?
            """, (variant_id,)).fetchone()
            
            if not row:
                return False, 0, "Variant not found"
            
            available = max(0, row["stock_quantity"])
            if available < requested_qty:
                return False, available, f"Only {available} timepiece(s) available"
            
            return True, available, "In Stock"

        if conn is not None:
            return _check(conn)
        with get_db() as c:
            return _check(c)

    @staticmethod
    def reserve_stock(variant_id, qty, order_number, conn=None):
        """Deducts stock from variant and parent product when order is placed."""
        def _reserve(c):
            cursor = c.cursor()
            cursor.execute("""
                SELECT stock_quantity
                FROM product_variants WHERE id = ?
            """, (variant_id,))
            row = cursor.fetchone()
            if not row or row["stock_quantity"] < qty:
                return False, "Insufficient inventory"

            new_stock = row["stock_quantity"] - qty
            cursor.execute("""
                UPDATE product_variants
                SET stock_quantity = ?
                WHERE id = ?
            """, (new_stock, variant_id))

            cursor.execute("""
                UPDATE products
                SET stock_quantity = stock_quantity - ?
                WHERE id = (SELECT product_id FROM product_variants WHERE id = ?)
            """, (qty, variant_id))

            cursor.execute("""
                INSERT INTO inventory_logs (variant_id, change_amount, new_stock, reason, reference_id)
                VALUES (?, ?, ?, 'ORDER_RESERVED', ?)
            """, (variant_id, -qty, new_stock, order_number))
            return True, "Stock reserved"

        if conn is not None:
            return _reserve(conn)
        with get_db() as c:
            return _reserve(c)

    @staticmethod
    def release_stock(variant_id, qty, order_number, conn=None):
        """Restores stock to variant and parent product when order is cancelled."""
        def _release(c):
            cursor = c.cursor()
            cursor.execute("SELECT stock_quantity FROM product_variants WHERE id = ?", (variant_id,))
            row = cursor.fetchone()
            if row:
                new_stock = row["stock_quantity"] + qty
                cursor.execute("""
                    UPDATE product_variants
                    SET stock_quantity = ?
                    WHERE id = ?
                """, (new_stock, variant_id))

                cursor.execute("""
                    UPDATE products
                    SET stock_quantity = stock_quantity + ?
                    WHERE id = (SELECT product_id FROM product_variants WHERE id = ?)
                """, (qty, variant_id))

                cursor.execute("""
                    INSERT INTO inventory_logs (variant_id, change_amount, new_stock, reason, reference_id)
                    VALUES (?, ?, ?, 'ORDER_CANCELLED_RELEASE', ?)
                """, (variant_id, qty, new_stock, order_number))
            return True, "Stock released"

        if conn is not None:
            return _release(conn)
        with get_db() as c:
            return _release(c)

    @staticmethod
    def finalize_stock(variant_id, qty, order_number, conn=None):
        """Finalizes stock deduction upon successful order completion."""
        def _finalize(c):
            cursor = c.cursor()
            cursor.execute("SELECT reserved_quantity FROM product_variants WHERE id = ?", (variant_id,))
            row = cursor.fetchone()
            if row:
                new_reserved = max(0, row["reserved_quantity"] - qty)
                cursor.execute("UPDATE product_variants SET reserved_quantity = ? WHERE id = ?", (new_reserved, variant_id))
            return True, "Stock finalized"

        if conn is not None:
            return _finalize(conn)
        with get_db() as c:
            return _finalize(c)
