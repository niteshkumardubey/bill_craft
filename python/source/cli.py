# ----------------------------- cli.py -----------------------------
from database import Database
from models import Product, Customer
from inventory import Inventory
from invoices import InvoiceManager

MENU = '''\
1) Add product
2) Add customer
0) Exit
Choose: '''

def interactive():
    db = Database()
    product_model = Product(db)
    customer_model = Customer(db)
    inventory_model = Inventory(db)
    invoice_manager = InvoiceManager(db)

    try:
        while True:
            try:
                choice = input(MENU).strip()
            except KeyboardInterrupt:
                print('\nExiting... Goodbye!')
                break

            if choice == '1':
                sku = input('SKU: ').strip()
                name = input('Name: ').strip()
                price = input('Price: ').strip()
                cost = input('Cost (optional): ').strip() or None
                reorder = input('Reorder level (int, default 0): ').strip() or '0'
                pid = product_model.add(sku, name, price, cost, int(reorder))
                print('Added product id', pid)

            elif choice == '2':
                name = input('Customer name: ').strip()
                email = input('Email: ').strip() or None
                phone = input('Phone: ').strip() or None
                address = input('Address: ').strip() or None
                cid = customer_model.add(name, email, phone, address)
                print('Added customer id', cid)

            elif choice == '0':
                print('Goodbye!')
                break

    finally:
        db.close()
