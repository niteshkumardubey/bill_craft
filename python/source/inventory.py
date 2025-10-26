# ----------------------------- inventory.py -----------------------------
from database import Database

class Inventory:
    def __init__(self, db: Database):
        self.db = db
    
    # Inventory movements (stock adjust)
    def adjust_stock(self, product_id, change, reason='adjustment'):
        from datetime import datetime
        now = datetime.utcnow().isoformat()
        cur = self.db.conn.cursor()
        cur.execute('INSERT INTO inventory_movements (product_id, change, reason, created_at) VALUES (?,?,?,?)',
                    (product_id, int(change), reason, now))
        self.db.conn.commit()
        return cur.lastrowid
    
    # Fetch available stoocks
    def get_stock(self, product_id):
        cur = self.db.conn.execute('SELECT IFNULL(SUM(change),0) as stock FROM inventory_movements WHERE product_id=?', (product_id,))
        r = cur.fetchone()
        return int(r['stock']) if r else 0
    
    # List of low stocks
    def low_stock_report(self):
        cur = self.conn.execute('''
            SELECT p.*, IFNULL((SELECT SUM(change) FROM inventory_movements im WHERE im.product_id=p.id),0) as stock
            FROM products p WHERE IFNULL((SELECT SUM(change) FROM inventory_movements im WHERE im.product_id=p.id),0) <= p.reorder_level
        ''')
        return cur.fetchall()