# ----------------------------- product.py -----------------------------
from database import Database, to_decimal

class Product:
    def __init__(self, db: Database):
        self.db = db
    
    # Add product
    def add_product(self, sku, name, price, cost=None, reorder_level=0):
        price = to_decimal(price)
        cost = to_decimal(cost) if cost else None
        cur = self.db.conn.cursor()
        cur.execute('INSERT INTO products (sku,name,price,cost,reorder_level) VALUES (?,?,?,?,?)',
                    (sku, name, str(price), str(cost) if cost else None, reorder_level))
        self.db.conn.commit()
        return cur.lastrowid
    
    # Update product
    def update_product(self, product_id, **fields):
        allowed = ['sku', 'name', 'price', 'cost', 'reorder_level']
        updates = []
        params = []
        for k, v in fields.items():
            if k in allowed and v is not None:
                if k in ('price', 'cost'):
                    v = str(to_decimal(v))
                updates.append(f"{k}=?")
                params.append(v)
        if not updates:
            return False
        params.append(product_id)
        sql = f"UPDATE products SET {', '.join(updates)} WHERE id=?"
        self.conn.execute(sql, params)
        self.conn.commit()
        return True
    
    # Search product by product ID
    def get_product(self, product_id):
        cur = self.conn.execute('SELECT * FROM products WHERE id=?', (product_id,))
        return cur.fetchone()
    
    # Search product by SKU and name
    def find_product_by_sku_or_name(self, term):
        cur = self.conn.execute("SELECT * FROM products WHERE sku LIKE ? OR name LIKE ?",
                                (f"%{term}%", f"%{term}%"))
        return cur.fetchall()
    
    # List of all products
    def list_products(self):
        cur = self.conn.execute('SELECT p.*, IFNULL((SELECT SUM(change) FROM inventory_movements im WHERE im.product_id=p.id),0) as stock FROM products p')
        return cur.fetchall()
