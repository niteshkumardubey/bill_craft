# ----------------------------- customer.py -----------------------------
from database import Database, to_decimal

class Customer:
    def __init__(self, db: Database):
        self.db = db
    
    # Add a new customer
    def add_customer(self, name, email=None, phone=None, address=None):
        cur = self.db.conn.cursor()
        cur.execute('INSERT INTO customers (name,email,phone,address) VALUES (?,?,?,?)', (name,email,phone,address))
        self.db.conn.commit()
        return cur.lastrowid
    
    # Update an existing customer
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
    
    # List of customers
    def list_customers(self):
        cur = self.conn.execute('SELECT * FROM customers')
        return cur.fetchall()