# ----------------------------- invoices.py -----------------------------
import csv, openpyxl
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from database import Database, to_decimal
from inventory import Inventory
from sales import SalesManager


class InvoiceManager:
    def __init__(self, db: Database):
        self.db = db
        self.inventory = Inventory(db)
    
    def _generate_invoice_no(self):
        """Generate invoice number like INV-YYYYMMDD-<count>"""
        datepart = datetime.utcnow().strftime('%Y%m%d')
        cur = self.db.conn.execute(
            "SELECT COUNT(*) as c FROM invoices WHERE date LIKE ?",
            (f"{datetime.utcnow().date()}%",)
        )
        count = cur.fetchone()['c']
        return f"INV-{datepart}-{count+1}"
        
    def create_invoice(self, items, customer_id=None, tax_rate=0, notes=None):
        """Creates a new invoice and deducts stock."""
        cur = self.db.conn.cursor()
        subtotal = Decimal('0.00')
        computed_items = []

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

        # Stock checks
        for it in computed_items:
            pid = it['product_id']
            if pid:
                stock = self.inventory.get_stock(pid)
                if it['qty'] > stock:
                    raise ValueError(f"Insufficient stock for product_id {pid}: have {stock}, need {it['qty']}")

        # Insert invoice
        cur.execute(
            'INSERT INTO invoices (invoice_no, customer_id, date, subtotal, tax, total, notes) VALUES (?,?,?,?,?,?,?)',
            (invoice_no, customer_id, now, str(subtotal), str(tax), str(total), notes)
        )
        inv_id = cur.lastrowid

        # Insert items and update stock
        for it in computed_items:
            cur.execute(
                'INSERT INTO invoice_items (invoice_id, product_id, description, qty, unit_price, line_total) VALUES (?,?,?,?,?,?)',
                (inv_id, it['product_id'], it['description'], it['qty'], it['unit_price'], it['line_total'])
            )
            if it['product_id']:
                self.inventory.adjust_stock(it['product_id'], -it['qty'], reason=f"sale invoice {invoice_no}")

        self.db.conn.commit()
        return inv_id

    def get_invoice(self, invoice_id):
        """Fetch invoice and its items"""
        cur = self.db.conn.execute('SELECT * FROM invoices WHERE id=?', (invoice_id,))
        inv = cur.fetchone()
        if not inv:
            return None
        items = self.db.conn.execute('SELECT * FROM invoice_items WHERE invoice_id=?', (invoice_id,)).fetchall()
        return inv, items

    def list_invoices(self, start_date=None, end_date=None):
        """List invoices by optional date range"""
        sql = 'SELECT * FROM invoices'
        params = []
        if start_date and end_date:
            sql += ' WHERE date BETWEEN ? AND ?'
            params = [start_date, end_date]
        cur = self.db.conn.execute(sql, params)
        return cur.fetchall()

    # Excel Export
    def export_sales_report_excel(self, filename="sales_report.xlsx", start_date=None, end_date=None):
        """Export sales report (summary + all invoices) to Excel"""
        sales = SalesManager(self.db)
        rows = self.list_invoices(start_date, end_date)
        summary = sales.sales_summary(start_date, end_date)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sales Report"

        headers = ["Invoice No", "Date", "Customer ID", "Subtotal", "Tax", "Total"]
        ws.append(headers)

        for r in rows:
            ws.append([
                r['invoice_no'],
                r['date'],
                r['customer_id'],
                float(r['subtotal']),
                float(r['tax']),
                float(r['total'])
            ])

        ws.append([])
        ws.append(["", "", "Total Invoices", summary['count']])
        ws.append(["", "", "Total Sales", float(summary['total_sales'])])

        # Auto column width
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[column].width = max_length + 2

        wb.save(filename)
        return filename

    # CSV Export
    def export_sales_report_csv(self, filename="sales_report.csv", start_date=None, end_date=None):
        """Export sales report (summary + all invoices) to CSV"""
        sales = SalesManager(self.db)
        rows = self.list_invoices(start_date, end_date)
        summary = sales.sales_summary(start_date, end_date)

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Invoice No", "Date", "Customer ID", "Subtotal", "Tax", "Total"])

            for r in rows:
                writer.writerow([
                    r['invoice_no'],
                    r['date'],
                    r['customer_id'],
                    r['subtotal'],
                    r['tax'],
                    r['total']
                ])

            writer.writerow([])
            writer.writerow(["", "", "Total Invoices", summary['count']])
            writer.writerow(["", "", "Total Sales", summary['total_sales']])

        return filename
