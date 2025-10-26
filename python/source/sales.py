# ----------------------------- sales.py -----------------------------
from database import Database, to_decimal

class SalesManager:
    def __init__(self, db: Database):
        self.db = db
    
    # sum totals and count invoices
    def sales_summary(self, start_date=None, end_date=None):
        sql = 'SELECT COUNT(*) as count, IFNULL(SUM(total),0) as total_sales FROM invoices'
        params = []
        if start_date and end_date:
            sql += ' WHERE date BETWEEN ? AND ?'
            params = [start_date, end_date]
        cur = self.db.conn.execute(sql, params)
        r = cur.fetchone()
        return {
            'count': r['count'],
            'total_sales': to_decimal(r['total_sales'])
        }