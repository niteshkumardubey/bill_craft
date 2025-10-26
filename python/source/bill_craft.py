"""
bill_craft.py

Starter accounting & inventory management application for N K Enterprises.
Language: Python 3 (no external dependencies)

Features included (starter):
- SQLite3 persistent storage (products, inventory, customers, invoices, invoice_items)
- Data models: Product, Customer, Invoice
- Core operations: add/update/delete products and customers, stock adjustments, create invoice (with stock check and decrement), view invoices
- Simple reports: inventory list, low-stock report, sales summary by date range
- Export invoice as CSV and backup DB
- Interactive command-line menu and argparse for scripted actions

How to run:
    python bill_craft.py

Notes & next steps:
- This is a single-file prototype. I can split into modules, add a web frontend (Flask/FastAPI), or GUI (Tkinter) on request.
- Add user authentication, roles, multi-user concurrency, and accounting entries (double-entry) if you want full accounting.

"""

import sqlite3
import os
import csv
import argparse
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

DB_FILENAME = 'mydatabase.db'

# ----------------------------- Utilities ---------------------------------

def to_decimal(x):
    """Convert number-like to Decimal and quantize to 2 dp."""
    return (Decimal(str(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def ensure_db(conn: sqlite3.Connection):
    c = conn.cursor()
    # products: id, sku, name, price (per unit), cost, stock
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            sku TEXT UNIQUE,
            name TEXT NOT NULL,
            price NUMERIC NOT NULL,
            cost NUMERIC,
            reorder_level INTEGER DEFAULT 0
        )
    ''')
    # customers
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            address TEXT
        )
    ''')
    # inventory table to keep stock movements (can be derived but useful)
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory_movements (
            id INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL,
            change INTEGER NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')
    # invoices and invoice items
    c.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY,
            invoice_no TEXT UNIQUE,
            customer_id INTEGER,
            date TEXT NOT NULL,
            subtotal NUMERIC NOT NULL,
            tax NUMERIC DEFAULT 0,
            total NUMERIC NOT NULL,
            notes TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY,
            invoice_id INTEGER NOT NULL,
            product_id INTEGER,
            description TEXT,
            qty INTEGER NOT NULL,
            unit_price NUMERIC NOT NULL,
            line_total NUMERIC NOT NULL,
            FOREIGN KEY(invoice_id) REFERENCES invoices(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')
    conn.commit()


# ----------------------------- Data operations ---------------------------

class Database:
    def __init__(self, filename=DB_FILENAME):
        self.filename = filename
        self.conn = sqlite3.connect(self.filename)
        self.conn.row_factory = sqlite3.Row
        ensure_db(self.conn)

    def close(self):
        self.conn.close()

    # Product operations
    def add_product(self, sku, name, price, cost=None, reorder_level=0):
        price = to_decimal(price)
        cost = to_decimal(cost) if cost is not None else None
        cur = self.conn.cursor()
        cur.execute('INSERT INTO products (sku,name,price,cost,reorder_level) VALUES (?,?,?,?,?)',
                    (sku, name, str(price), str(cost) if cost is not None else None, reorder_level))
        pid = cur.lastrowid
        # initialize inventory movement with zero stock (optional)
        self.conn.commit()
        return pid

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

    def get_product(self, product_id):
        cur = self.conn.execute('SELECT * FROM products WHERE id=?', (product_id,))
        return cur.fetchone()

    def find_product_by_sku_or_name(self, term):
        cur = self.conn.execute("SELECT * FROM products WHERE sku LIKE ? OR name LIKE ?",
                                (f"%{term}%", f"%{term}%"))
        return cur.fetchall()

    def list_products(self):
        cur = self.conn.execute('SELECT p.*, IFNULL((SELECT SUM(change) FROM inventory_movements im WHERE im.product_id=p.id),0) as stock FROM products p')
        return cur.fetchall()

    # Inventory movements (stock adjust)
    def adjust_stock(self, product_id, change, reason='adjustment'):
        now = datetime.utcnow().isoformat()
        cur = self.conn.cursor()
        cur.execute('INSERT INTO inventory_movements (product_id, change, reason, created_at) VALUES (?,?,?,?)',
                    (product_id, int(change), reason, now))
        self.conn.commit()
        return cur.lastrowid

    def get_stock(self, product_id):
        cur = self.conn.execute('SELECT IFNULL(SUM(change),0) as stock FROM inventory_movements WHERE product_id=?', (product_id,))
        r = cur.fetchone()
        return int(r['stock']) if r else 0

    def low_stock_report(self):
        cur = self.conn.execute('''
            SELECT p.*, IFNULL((SELECT SUM(change) FROM inventory_movements im WHERE im.product_id=p.id),0) as stock
            FROM products p WHERE IFNULL((SELECT SUM(change) FROM inventory_movements im WHERE im.product_id=p.id),0) <= p.reorder_level
        ''')
        return cur.fetchall()

    # Customer operations
    def add_customer(self, name, email=None, phone=None, address=None):
        cur = self.conn.cursor()
        cur.execute('INSERT INTO customers (name,email,phone,address) VALUES (?,?,?,?)', (name, email, phone, address))
        self.conn.commit()
        return cur.lastrowid

    def update_customer(self, customer_id, **fields):
        allowed = ['name', 'email', 'phone', 'address']
        updates = []
        params = []
        for k, v in fields.items():
            if k in allowed and v is not None:
                updates.append(f"{k}=?")
                params.append(v)
        if not updates:
            return False
        params.append(customer_id)
        sql = f"UPDATE customers SET {', '.join(updates)} WHERE id=?"
        self.conn.execute(sql, params)
        self.conn.commit()
        return True

    def list_customers(self):
        cur = self.conn.execute('SELECT * FROM customers')
        return cur.fetchall()

    # Invoice operations
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

    def sales_summary(self, start_date=None, end_date=None):
        # sum totals and count invoices
        sql = 'SELECT COUNT(*) as count, IFNULL(SUM(total),0) as total_sales FROM invoices'
        params = []
        if start_date and end_date:
            sql += ' WHERE date BETWEEN ? AND ?'
            params = [start_date, end_date]
        cur = self.conn.execute(sql, params)
        r = cur.fetchone()
        return {'count': r['count'], 'total_sales': Decimal(str(r['total_sales'])).quantize(Decimal('0.01'))}

    # Export
    def export_invoice_csv(self, invoice_id, outpath):
        inv_data = self.get_invoice(invoice_id)
        if not inv_data:
            raise ValueError('Invoice not found')
        inv, items = inv_data
        with open(outpath, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Invoice No', inv['invoice_no']])
            w.writerow(['Date', inv['date']])
            w.writerow(['Customer ID', inv['customer_id']])
            w.writerow([])
            w.writerow(['Description','Qty','Unit Price','Line Total'])
            for it in items:
                w.writerow([it['description'], it['qty'], it['unit_price'], it['line_total']])
            w.writerow([])
            w.writerow(['Subtotal', inv['subtotal']])
            w.writerow(['Tax', inv['tax']])
            w.writerow(['Total', inv['total']])
        return outpath

    def backup_db(self, backup_path):
        self.conn.commit()
        self.conn.close()
        import shutil
        shutil.copyfile(self.filename, backup_path)
        self.conn = sqlite3.connect(self.filename)
        self.conn.row_factory = sqlite3.Row
        return backup_path


# ----------------------------- Simple CLI --------------------------------

MENU = '''
Main Menu
1) Add product
2) List products
3) Adjust stock
4) Add customer
5) List customers
6) Create invoice
7) View invoice
8) Export invoice CSV
9) Low stock report
10) Sales summary
0) Exit
Choose: '''


def interactive():
    db = Database()
    try:
        while True:
            try:
                choice = input(MENU).strip()
            except KeyboardInterrupt:
                print("\n\nExiting... Goodbye!\n")
                break
                
            if choice == '1': # Add product
                sku = input('SKU: ').strip()
                name = input('Name: ').strip()
                price = input('Price: ').strip()
                cost = input('Cost (optional): ').strip() or None
                reorder = input('Reorder level (int, default 0): ').strip() or '0'
                pid = db.add_product(sku, name, price, cost, int(reorder))
                print('Added product id', pid)
                
            elif choice == '2': # List products
                rows = db.list_products()
                print('ID | SKU | Name | Price | Stock')
                for r in rows:
                    print(f"{r['id']} | {r['sku']} | {r['name']} | {r['price']} | {r['stock']}")
                    
            elif choice == '3': # Adjust stock
                pid = int(input('Product id: '))
                change = int(input('Change (+ve to add, -ve to remove): '))
                reason = input('Reason: ').strip() or 'manual'
                db.adjust_stock(pid, change, reason)
                print('Stock adjusted.')
                
            elif choice == '4': # Add customer
                name = input('Customer name: ').strip()
                email = input('Email: ').strip() or None
                phone = input('Phone: ').strip() or None
                address = input('Address: ').strip() or None
                cid = db.add_customer(name, email, phone, address)
                print('Added customer id', cid)
                
            elif choice == '5': # List customers
                rows = db.list_customers()
                print('ID | Name | Email | Phone')
                for r in rows:
                    print(f"{r['id']} | {r['name']} | {r['email']} | {r['phone']}")
                    
            elif choice == '6': # Create invoice
                print('Creating invoice. Enter line items. Blank description to finish.')
                items = []
                while True:
                    desc = input('Description (or product id if numeric): ').strip()
                    if desc == '':
                        break
                    # try parse as product id
                    product_id = None
                    description = desc
                    if desc.isdigit():
                        product_id = int(desc)
                        prod = db.get_product(product_id)
                        if prod:
                            description = prod['name']
                            unit_price = prod['price']
                        else:
                            print('Product not found.')
                            continue
                    else:
                        unit_price = input('Unit price: ').strip()
                    qty = int(input('Qty: ').strip())
                    items.append({'product_id': product_id, 'description': description, 'qty': qty, 'unit_price': unit_price})
                tax = input('Tax rate % (e.g., 5): ').strip() or '0'
                customer = input('Customer id (optional): ').strip() or None
                customer = int(customer) if customer else None
                try:
                    inv_id = db.create_invoice(items, customer_id=customer, tax_rate=to_decimal(tax))
                    print('Created invoice id', inv_id)
                except Exception as e:
                    print('Error creating invoice:', e)
                    
            elif choice == '7': # View invoice
                iid = int(input('Invoice id: '))
                invdata = db.get_invoice(iid)
                if not invdata:
                    print('Not found')
                else:
                    inv, items = invdata
                    print('Invoice:', inv['invoice_no'], inv['date'])
                    print('Subtotal:', inv['subtotal'], 'Tax:', inv['tax'], 'Total:', inv['total'])
                    for it in items:
                        print('-', it['description'], it['qty'], it['unit_price'], it['line_total'])
                        
            elif choice == '8': # Export invoice CSV
                iid = int(input('Invoice id: '))
                out = input('Output CSV filename: ').strip() or f"invoice_{iid}.csv"
                try:
                    path = db.export_invoice_csv(iid, out)
                    print('Exported to', path)
                except Exception as e:
                    print('Error:', e)
                    
            elif choice == '9': # Low stock report
                rows = db.low_stock_report()
                for r in rows:
                    print(f"{r['id']} {r['name']} stock={r['stock']} reorder_level={r['reorder_level']}")
                    
            elif choice == '10': # Sales summary
                s = input('Start date (YYYY-MM-DD) or blank: ').strip() or None
                e = input('End date (YYYY-MM-DD) or blank: ').strip() or None
                summary = db.sales_summary(start_date=s, end_date=e)
                print('Invoices:', summary['count'], 'Total sales:', summary['total_sales'])
                
            elif choice == '0': # Exit
                break
                
            else:
                print('Unknown choice')
    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting safely...")
    finally:
        db.close()


# ----------------------------- Argparse wrapper --------------------------

def main():
    parser = argparse.ArgumentParser(description='NKEnterprises accounting CLI')
    parser.add_argument('--init-sample', action='store_true', help='Create sample data and exit')
    parser.add_argument('--backup', help='Backup database to path')
    parser.add_argument('--interactive', action='store_true', help='Run interactive menu')
    args = parser.parse_args()

    db = Database()
    try:
        if args.init_sample:
            # create sample product/customer
            pid = db.add_product('SKU-001', 'Sample Widget', '99.50', '60.00', reorder_level=5)
            db.adjust_stock(pid, 20, reason='initial stock')
            cid = db.add_customer('Acme Corporation', 'sales@acme.example', '+123456789')
            print('Created sample product id', pid, 'and customer id', cid)
            return
        if args.backup:
            path = db.backup_db(args.backup)
            print('Backed up DB to', path)
            return
        if args.interactive or (not any(vars(args).values())):
            interactive()
    finally:
        db.close()


if __name__ == '__main__':
    main()
