# ----------------------------- invoices.py -----------------------------
from database import Database, to_decimal

class InvoiceManager:
    def __init__(self, db: Database):
        self.db = db
    
    def _generate_invoice_no(self):
        # Simple invoice numbering: INV-YYYYMMDD-<count>
        datepart = datetime.utcnow().strftime('%Y%m%d')
        cur = self.conn.execute("SELECT COUNT(*) as c FROM invoices WHERE date LIKE ?", (f"{datetime.utcnow().date()}%",))
        count = cur.fetchone()['c']
        return f"INV-{datepart}-{count+1}"
        
    def create_invoice(self, items, customer_id=None, tax_rate=0, notes=None):
        """
        items: list of dicts {product_id(optional), description, qty, unit_price}
        Will check stock for product_id entries and decrement stock (creates inventory_movements)
        Returns invoice id
        """
        cur = self.conn.cursor()
        subtotal = Decimal('0.00')
        computed_items = []
        # Validate and compute line totals using Decimal
        for it in items:
            qty = int(it['qty'])
            unit = to_decimal(it['unit_price'])
            line = (unit * Decimal(qty)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            subtotal += line
            computed_items.append({
                'product_id': it.get('product_id'),
                'description': it.get('description') or '',
                'qty': qty,
                'unit_price': str(unit),
                'line_total': str(line)
            })
        tax = (subtotal * to_decimal(tax_rate) / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total = (subtotal + tax).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        invoice_no = self._generate_invoice_no()
        now = datetime.utcnow().isoformat()

        # stock checks
        for it in computed_items:
            pid = it['product_id']
            if pid:
                stock = self.get_stock(pid)
                if it['qty'] > stock:
                    raise ValueError(f"Insufficient stock for product_id {pid}: have {stock}, need {it['qty']}")

        cur.execute('INSERT INTO invoices (invoice_no, customer_id, date, subtotal, tax, total, notes) VALUES (?,?,?,?,?,?,?)',
                    (invoice_no, customer_id, now, str(subtotal), str(tax), str(total), notes))
        inv_id = cur.lastrowid
        # insert items
        for it in computed_items:
            cur.execute('INSERT INTO invoice_items (invoice_id, product_id, description, qty, unit_price, line_total) VALUES (?,?,?,?,?,?)',
                        (inv_id, it['product_id'], it['description'], it['qty'], it['unit_price'], it['line_total']))
            # decrement stock
            if it['product_id']:
                self.adjust_stock(it['product_id'], -it['qty'], reason=f"sale invoice {invoice_no}")
        self.conn.commit()
        return inv_id

    def get_invoice(self, invoice_id):
        cur = self.conn.execute('SELECT * FROM invoices WHERE id=?', (invoice_id,))
        inv = cur.fetchone()
        if not inv:
            return None
        items = self.conn.execute('SELECT * FROM invoice_items WHERE invoice_id=?', (invoice_id,)).fetchall()
        return inv, items

    def list_invoices(self, start_date=None, end_date=None):
        sql = 'SELECT * FROM invoices'
        params = []
        if start_date and end_date:
            sql += ' WHERE date BETWEEN ? AND ?'
            params = [start_date, end_date]
        cur = self.conn.execute(sql, params)
        return cur.fetchall()