# ----------------------------- main_backend.py -----------------------------
import argparse
from menu import interactive
from database import Database

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