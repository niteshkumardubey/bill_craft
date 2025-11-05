# ----------------------------- menu.py -----------------------------
from database import Database, to_decimal
from inventory import Inventory
from customer import Customer
from invoices import InvoiceManager
from sales import SalesManager
from product import Product

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
11) Export invoice PDF
0) Exit
Choose: '''

def interactive():
    try:
        # create one database connection
        db = Database()
        product = Product(db)
        customer = Customer(db)
        inventory = Inventory(db)
        invoice = InvoiceManager(db)
        sales = SalesManager(db)

        while True:
            try:
                choice = input(MENU).strip()
            except KeyboardInterrupt:
                print("\n\nExiting... Goodbye!\n")
                break

            if choice == '1':  # Add product
                sku = input('SKU: ').strip()
                name = input('Name: ').strip()
                price = input('Selling Price: ').strip()
                cost = input('Cost Price (optional): ').strip() or None
                reorder = input('Reorder level (int, default 0): ').strip() or '0'
                pid = product.add_product(sku, name, price, cost, int(reorder))
                print('Added product id', pid)

            elif choice == '2':  # List products
                rows = product.list_products()
                print('ID | SKU | Name | Price | Stock')
                for r in rows:
                    print(f"{r['id']} | {r['sku']} | {r['name']} | {r['price']} | {r['stock']}")

            elif choice == '3':  # Adjust stock
                pid = int(input('Product id: '))
                change = int(input('Change (+ve to add, -ve to remove): '))
                reason = input('Reason: ').strip() or 'manual'
                inventory.adjust_stock(pid, change, reason)
                print('Stock adjusted.')

            elif choice == '4':  # Add customer
                name = input('Customer name: ').strip()
                email = input('Email: ').strip() or None
                phone = input('Phone: ').strip() or None
                address = input('Address: ').strip() or None
                cid = customer.add_customer(name, email, phone, address)
                print('Added customer id', cid)

            elif choice == '5':  # List customers
                rows = customer.list_customers()
                print('ID | Name | Email | Phone')
                for r in rows:
                    print(f"{r['id']} | {r['name']} | {r['email']} | {r['phone']}")

            elif choice == '6':  # Create invoice
                print('Creating invoice. Enter line items. Blank description to finish.')
                items = []
                while True:
                    desc = input('Description (or product id if numeric): ').strip()
                    if desc == '':
                        break
                    product_id = None
                    description = desc
                    if desc.isdigit():
                        product_id = int(desc)
                        prod = product.get_product(product_id)
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
                customer_id = input('Customer id (optional): ').strip() or None
                customer_id = int(customer_id) if customer_id else None
                try:
                    inv_id = invoice.create_invoice(items, customer_id=customer_id, tax_rate=to_decimal(tax))
                    print('Created invoice id', inv_id)
                except Exception as e:
                    print('Error creating invoice:', e)

            elif choice == '7':  # View invoice
                iid = int(input('Invoice id: '))
                invdata = invoice.get_invoice(iid)
                if not invdata:
                    print('Not found')
                else:
                    inv, items = invdata
                    print('Invoice:', inv['invoice_no'], inv['date'])
                    print('Subtotal:', inv['subtotal'], 'Tax:', inv['tax'], 'Total:', inv['total'])
                    for it in items:
                        print('-', it['description'], it['qty'], it['unit_price'], it['line_total'])

            elif choice == '8':  # Export invoice CSV
                iid = int(input('Invoice id: '))
                out = input('Output CSV filename: ').strip() or f"invoice_{iid}.csv"
                try:
                    path = invoice.export_single_invoice_csv(iid, out)
                    print('Exported to', path)
                except Exception as e:
                    print('Error:', e)

            elif choice == '9':  # Low stock report
                rows = inventory.low_stock_report()
                for r in rows:
                    print(f"{r['id']} {r['name']} stock={r['stock']} reorder_level={r['reorder_level']}")

            elif choice == '10':  # Sales summary
                s = input('Start date (YYYY-MM-DD) or blank: ').strip() or None
                e = input('End date (YYYY-MM-DD) or blank: ').strip() or None
                summary = sales.sales_summary(start_date=s, end_date=e)
                print('Invoices:', summary['count'], 'Total sales:', summary['total_sales'])

            elif choice == '11':  # Export invoice PDF
                iid = int(input('Invoice id: '))
                out = input('Output PDF filename: ').strip() or f"invoice_{iid}.pdf"
                try:
                    path = invoice.export_single_invoice_pdf(iid, out)
                    print('Exported PDF to', path)
                except Exception as e:
                    print('Error:', e)

            elif choice == '0':  # Exit
                print("Goodbye!")
                break

            else:
                print('Unknown choice')

    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting safely...")
    finally:
        db.close()
