# NKEnterprises Accounting & Inventory System

Language: Python 3
Database: SQLite3 (no external dependencies)
Purpose: Lightweight offline accounting + inventory management system for small businesses (e.g., N K Enterprises)


# Features:
🧱 Modular design (Product, Customer, Inventory, Invoices, Sales)
💾 Persistent SQLite storage
📦 Stock tracking & low-stock alerts
🧮 Invoice generation with tax & stock deduction
📊 Sales summaries & reports
📤 Export invoices / reports to CSV
🧑‍💼 Interactive command-line menu
🧰 Simple database backup utility


# Architecture Diagram
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
All modules depend on database.py, which provides:
1. The SQLite connection
2. Schema creation
3. Utility to_decimal() for currency precision

# Module Overview
| Module                | Description                                                                | Key Classes / Functions                   |
| --------------------- | -------------------------------------------------------------------------- | ----------------------------------------- |
| **`database.py`**     | Manages DB connection, creates tables, and defines helper functions.       | `Database`, `to_decimal()`, `ensure_db()` |
| **`product.py`**      | Handles product CRUD operations, SKU/name search, and stock-aware listing. | `Product`                                 |
| **`customer.py`**     | CRUD operations for customer records.                                      | `Customer`                                |
| **`inventory.py`**    | Tracks stock movements, provides stock level and low-stock report.         | `Inventory`                               |
| **`invoices.py`**     | Creates invoices, validates stock, exports to CSV.                         | `InvoiceManager`                          |
| **`sales.py`**        | Summarizes invoice totals for reporting.                                   | `SalesManager`                            |
| **`menu.py`**         | CLI menu connecting all modules for human interaction.                     | `interactive()`                           |
| **`main_backend.py`** | Entry point using `argparse` (init, backup, or menu).                      | `main()`                                  |


# Data Model Summary
| Table                 | Purpose                | Key Columns                                                     |
| --------------------- | ---------------------- | --------------------------------------------------------------- |
| `products`            | Stores product catalog | `sku`, `name`, `price`, `reorder_level`                         |
| `customers`           | Stores customer info   | `name`, `email`, `phone`, `address`                             |
| `inventory_movements` | Tracks stock changes   | `product_id`, `change`, `reason`, `created_at`                  |
| `invoices`            | Header of invoices     | `invoice_no`, `date`, `subtotal`, `tax`, `total`, `customer_id` |
| `invoice_items`       | Line items             | `invoice_id`, `product_id`, `qty`, `unit_price`, `line_total`   |


# Future Enhancements

🔐 User authentication and roles
🌐 Web interface (Flask / FastAPI)
🧾 PDF invoice generation
💹 Profit & loss / balance sheet reports
☁️ Multi-user concurrent access