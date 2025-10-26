# ----------------------------- database.py -----------------------------
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

DB_FILENAME = 'nkenterprises.db'

def to_decimal(x):
    return Decimal(str(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

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

class Database:
    def __init__(self, filename=DB_FILENAME):
        self.filename = filename
        self.conn = sqlite3.connect(self.filename)
        self.conn.row_factory = sqlite3.Row
        ensure_db(self.conn)

    def close(self):
        self.conn.close()
    
    def backup_db(self, backup_path):
        self.conn.commit()
        self.conn.close()
        import shutil
        shutil.copyfile(self.filename, backup_path)
        self.conn = sqlite3.connect(self.filename)
        self.conn.row_factory = sqlite3.Row
        return backup_path