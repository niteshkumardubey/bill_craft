# 🧾 NKEnterprises Accounting & Inventory System

**Language:** Python 3  
**Database:** SQLite3 (no external dependencies)  
**Purpose:** Lightweight offline accounting + inventory management system for small businesses (e.g., N K Enterprises)

---

## 🚀 Features

- 🧱 **Modular design** (Product, Customer, Inventory, Invoices, Sales)
- 💾 **Persistent SQLite storage**
- 📦 **Stock tracking & low-stock alerts**
- 🧮 **Invoice generation with tax & stock deduction**
- 📊 **Sales summaries & reports**
- 📤 **Export invoices / reports to CSV**
- 🧑‍💼 **Interactive command-line menu**
- 🧰 **Simple database backup utility**

---

## 📂 Project Structure

```
nk_enterprises/
│
├── main_backend.py       # Entry point (CLI)
├── menu.py               # Interactive CLI menu
│
├── database.py           # Database connection + schema
├── product.py            # Product management (CRUD)
├── customer.py           # Customer management (CRUD)
├── inventory.py          # Stock tracking
├── invoices.py           # Invoice generation & export
├── sales.py              # Sales summaries / reports
│
├── mydatabase.db         # SQLite database (auto-created)
└── README.md             # Documentation
```

---

## 🧭 Architecture Diagram

```
               ┌───────────────────────────┐
               │       main_backend.py     │
               │  (entry point / argparse) │
               └──────────────┬────────────┘
                              │
                              ▼
                   ┌────────────────────┐
                   │       menu.py      │
                   │  (interactive CLI) │
                   └─────────┬──────────┘
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
 ┌─────────────────┐ ┌─────────────────┐ ┌──────────────────┐
 │   product.py    │ │  customer.py    │ │  inventory.py     │
 │  (Product CRUD) │ │ (Customer CRUD) │ │ (Stock handling)  │
 └────────┬────────┘ └────────┬────────┘ └────────┬──────────┘
          │                   │                   │
          └───────────────┬────┴────┬─────────────┘
                          ▼         ▼
                 ┌────────────────────────┐
                 │     invoices.py        │
                 │ (Invoice creation, CSV)│
                 └───────────┬────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │    sales.py      │
                    │ (Sales summary)  │
                    └──────────────────┘
```

All modules depend on **`database.py`**, which provides:
- The SQLite connection
- Schema creation
- Utility `to_decimal()` for currency precision

---

## ⚙️ How to Run

### 1. Initialize environment
```bash
python main_backend.py --init-sample
```
This will create:
- A sample product (`SKU-001`)
- A sample customer (`Acme Corporation`)
- And initialize stock levels

### 2. Start the interactive menu
```bash
python main_backend.py --interactive
```

### 3. (Optional) Backup database
```bash
python main_backend.py --backup backup_nkenterprises.db
```

---

## 🧩 Module Overview

| Module | Description | Key Classes / Functions |
|---------|--------------|--------------------------|
| **`database.py`** | Manages DB connection, creates tables, and defines helper functions. | `Database`, `to_decimal()`, `ensure_db()` |
| **`product.py`** | Handles product CRUD operations, SKU/name search, and stock-aware listing. | `Product` |
| **`customer.py`** | CRUD operations for customer records. | `Customer` |
| **`inventory.py`** | Tracks stock movements, provides stock level and low-stock report. | `Inventory` |
| **`invoices.py`** | Creates invoices, validates stock, exports to CSV. | `InvoiceManager` |
| **`sales.py`** | Summarizes invoice totals for reporting. | `SalesManager` |
| **`menu.py`** | CLI menu connecting all modules for human interaction. | `interactive()` |
| **`main_backend.py`** | Entry point using `argparse` (init, backup, or menu). | `main()` |

---

## 🧠 Data Model Summary

| Table | Purpose | Key Columns |
|--------|----------|-------------|
| `products` | Stores product catalog | `sku`, `name`, `price`, `reorder_level` |
| `customers` | Stores customer info | `name`, `email`, `phone`, `address` |
| `inventory_movements` | Tracks stock changes | `product_id`, `change`, `reason`, `created_at` |
| `invoices` | Header of invoices | `invoice_no`, `date`, `subtotal`, `tax`, `total`, `customer_id` |
| `invoice_items` | Line items | `invoice_id`, `product_id`, `qty`, `unit_price`, `line_total` |

---

## 📤 CSV Export Examples

### Export a single invoice:
```bash
python main_backend.py --interactive
# then choose option 8
```

Output → `invoice_<id>.csv` (includes customer + line items)

### Export all sales:
Inside `invoices.py`, use:
```python
invoice.export_sales_report_csv("sales_report.csv")
```

---

## 🧱 Future Enhancements

- 🔐 User authentication and roles  
- 🌐 Web interface (Flask / FastAPI)  
- 🧾 PDF invoice generation  
- 💹 Profit & loss / balance sheet reports  
- ☁️ Multi-user concurrent access  
