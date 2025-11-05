# ----------------------------- invoices.py -----------------------------
import os
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from database import Database, to_decimal
from inventory import Inventory
from sales import SalesManager
from customer import Customer

# -------------- For CSV files ---------------------
import csv, openpyxl

# -------------- For pdf files ---------------------
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping


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

    # CSV Export
    def export_single_invoice_csv(self, invoice_id, filename=None):
        """Export a single invoice with its items + customer details to CSV"""
        inv, items = self.get_invoice(invoice_id)
        if not inv:
            raise ValueError("Invoice not found")

        # Fetch customer details
        cust_obj = Customer(self.db)
        cust = cust_obj.get_customer(inv["customer_id"])

        # Convert sqlite3.Row to dict if not None
        if cust:
            cust = dict(cust)

        # File name handling
        if not filename:
            filename = f"invoice_{invoice_id}.csv"
        elif not filename.lower().endswith(".csv"):
            filename += ".csv"

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ====== Header Section ======
            writer.writerow(["Invoice Export"])
            writer.writerow([])

            # Customer details section
            writer.writerow(["Customer Details"])
            writer.writerow(["Customer ID", "Name", "Email", "Phone", "Address"])
            if cust:
                writer.writerow([
                    cust.get("id", ""),
                    cust.get("name", ""),
                    cust.get("email", ""),
                    cust.get("phone", ""),
                    cust.get("address", "")
                ])
            else:
                writer.writerow(["N/A", "N/A", "N/A", "N/A", "N/A"])
            writer.writerow([])

            # Invoice summary
            writer.writerow(["Invoice Info"])
            writer.writerow(["Invoice No", "Date", "Subtotal", "Tax", "Total"])
            writer.writerow([inv["invoice_no"], inv["date"], inv["subtotal"], inv["tax"], inv["total"]])
            writer.writerow([])

            # Line Items
            writer.writerow(["Line Items"])
            writer.writerow(["Description", "Qty", "Unit Price", "Line Total"])
            for it in items:
                writer.writerow([it["description"], it["qty"], it["unit_price"], it["line_total"]])

        return filename

    def export_single_invoice_pdf(self, invoice_id, filename=None):
        """Export a single invoice (with customer details & items) to PDF"""

        # ---------- FONT ----------
        base_dir = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.abspath(os.path.join(base_dir, "..", "Fonts", "dejavu-fonts-ttf-2.37", "ttf", "DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))
        addMapping("DejaVuSans", 0, 0, "DejaVuSans")

        # ---------- FETCH DATA ----------
        inv, items = self.get_invoice(invoice_id)
        if not inv:
            raise ValueError("Invoice not found")
        
        cust_obj = Customer(self.db)
        cust = cust_obj.get_customer(inv["customer_id"])
        if cust:
            cust = dict(cust)

        # ---------- OUTPUT PATH ----------
        if not filename:
            filename = f"invoice_{invoice_id}.pdf"
        elif not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        # ---------- SETUP PDF ----------
        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        for s in styles.byName.values():
            s.fontName = "DejaVuSans"
        elements = []

        # ---------- COMPANY LOGO ----------
        logo_path = os.path.join(base_dir, "..", "Assets", "logo.png")
        if os.path.exists(logo_path):
            img = Image(logo_path, width=100, height=100)
            elements.append(img)
        else:
            elements.append(Paragraph("<b>N K Enterprises</b>", styles["Title"]))
        elements.append(Spacer(1, 12))

        # ---------- HEADER ----------
        elements.append(Paragraph("<b>Tax Invoice</b>", styles["Title"]))
        elements.append(Spacer(1, 10))

        # ---------- CUSTOMER DETAILS ----------
        elements.append(Paragraph("<b>Customer Details:</b>", styles["Heading3"]))
        if cust:
            cust_text = f"""
            <b>Name:</b> {cust.get('name', '')}<br/>
            <b>Email:</b> {cust.get('email', '')}<br/>
            <b>Phone:</b> {cust.get('phone', '')}<br/>
            <b>Address:</b> {cust.get('address', '')}
            """
        else:
            cust_text = "N/A"
        elements.append(Paragraph(cust_text, styles["Normal"]))
        elements.append(Spacer(1, 12))

        # ---------- INVOICE SUMMARY ----------
        inv_info = f"""
        <b>Invoice No:</b> {inv['invoice_no']}<br/>
        <b>Date:</b> {inv['date']}<br/>
        <b>Subtotal:</b> ₹{inv['subtotal']}<br/>
        <b>Tax:</b> ₹{inv['tax']}<br/>
        <b>Total:</b> ₹{inv['total']}
        """
        elements.append(Paragraph("<b>Invoice Summary:</b>", styles["Heading3"]))
        elements.append(Paragraph(inv_info, styles["Normal"]))
        elements.append(Spacer(1, 12))

        # ---------- LINE ITEMS TABLE ----------
        data = [["Description", "Qty", "Unit Price", "Line Total"]]
        for it in items:
            data.append([
                it["description"],
                str(it["qty"]),
                str(it["unit_price"]),
                str(it["line_total"]),
            ])
        table = Table(data, colWidths=[200, 60, 80, 80])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "DejaVuSans"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ]))
        elements.append(Paragraph("<b>Invoice Items:</b>", styles["Heading3"]))
        elements.append(table)
        elements.append(Spacer(1, 25))

        # ---------- SIGNATURE SECTION ----------
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("<b>For N K Enterprises</b>", styles["Normal"]))
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("__________________________", styles["Normal"]))
        elements.append(Paragraph("<b>Authorized Signature</b>", styles["Normal"]))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("<b>Thank you for your business!</b>", styles["Normal"]))

        # ---------- BUILD PDF ----------
        doc.build(elements)
        return filename

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
