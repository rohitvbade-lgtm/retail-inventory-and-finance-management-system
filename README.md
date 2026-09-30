# Apex POS & Finance Management with AI Discount Machine

A modern full-stack retail management system built with **FastAPI (Python)** and **Angular**, designed for store owners to manage inventory with low-stock alerts, handle counter reception checkout with automated invoice generation, and configure intelligent discounts using natural language via an **AI-driven Deterministic Discount Engine**.

---

## 🌟 Key Features

### 1. Real-Time Inventory Management & Low-Stock Alerts
- **Product Catalog**: Track product name, SKU, category, price, cost price, current stock quantity, and minimum alert threshold.
- **Stock Threshold Alerts**: Automated notification system alerting the owner whenever any product's stock drops to or below its `min_threshold`.
- **Quick Restock**: One-click restock buttons (+5, +10, +25, +50, or custom amounts) directly from the alert banner or inventory table.
- **Automatic Stock Deduction**: As counter sales complete, the inventory is atomically deducted.

### 2. Finance Management & Counter Invoicing (POS)
- **Counter Reception Terminal**: Fast product catalog search, category filtering, and one-click cart additions.
- **Live Discount Engine Integration**: As items are added or quantities modified, the cart preview automatically queries the deterministic discount engine, presenting real-time itemized savings and applied discount rules.
- **Simulation Mode**: Built-in test switch allowing the cashier/owner to simulate checkout as "Weekend (Sat)", "Weekday (Wed)", or "Actual Day" to test time-based discount rules on the spot.
- **Instant Checkout & Invoice Generation**: Creates formatted invoice records (`INV-YYYYMMDD-####`), logs customer details, updates revenue metrics, and prints itemized paper receipts.
- **Finance Analytics Dashboard**: Real-time sales metrics, revenue, discounts given, and invoice history lookup.

### 3. AI Discount Machine (Deterministic & Extensible)
- **Natural Language Chatbox**: Store owners configure discounts simply by typing natural language prompts:
  - *"Give 15% discount on all dairy products this weekend"*
  - *"Apply $5 off on orders over $40 on weekdays"*
  - *"Autumn promo: 20% discount on Bakery products until tomorrow"*
  - *"Deactivate all weekend discounts"*
  - *"What discounts are currently active?"*
- **Deterministic Discount Engine (`DeterministicDiscountEngine`)**:
  - Pure, deterministic evaluation pattern (zero guesswork, 100% repeatable audit trail).
  - Evaluates schedules (`WEEKEND`, `WEEKDAY`, `ALWAYS`, `DATE_RANGE` / seasonal).
  - Evaluates scopes (`PRODUCT`, `CATEGORY`, `ENTIRE_ORDER`).
  - Evaluates minimum spend thresholds (`min_order_amount`).
- **AI Dual-Engine Architecture**:
  - **Gemini API Integration**: Uses Google's Gemini models via `google-genai` SDK for structured tool-calling when an API key is provided.
  - **Built-in Deterministic NLU Parser**: Operates seamlessly offline out-of-the-box without requiring an API key.
- **Interactive Rule Sandbox**: A live test bench to test baskets against active rules and verify qualification logic.

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: 3.12+ (or UV)
- **Node.js**: v20+ & **npm**

### Option A: 1-Click Launch (Windows)
Double click `start_all.bat` or run:
```powershell
.\start_all.ps1
```

### Option B: Manual Startup

#### 1. Start the Python Backend
```bash
# Activate virtual environment
.venv\Scripts\activate

# Launch FastAPI backend with auto-reload
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend will automatically create SQLite database `inventory_finance.db` and populate it with sample products, discount rules, and initial invoices.
- **Backend API**: `http://localhost:8000`
- **Swagger Docs**: `http://localhost:8000/docs`

#### 2. Start the Angular Frontend
```bash
cd frontend
npm start
```
- **Web App**: `http://localhost:4200`

---

## 🧪 Running System Verification Tests

Run the end-to-end integration test to verify all backend systems, inventory alerts, AI prompt parsing, discount calculations, and counter checkout:
```bash
.venv\Scripts\python.exe test_system.py
```

---

## 📁 Project Structure

```
├── backend/
│   ├── database.py              # SQLite & SQLAlchemy engine setup
│   ├── models.py                # ORM models: Product, DiscountRule, Invoice, etc.
│   ├── schemas.py               # Pydantic validation schemas
│   ├── discount_engine.py       # Deterministic rule evaluation engine
│   ├── ai_service.py            # AI Prompt handler (Gemini + Deterministic NLU)
│   ├── seed_data.py             # Demo products, initial discounts & invoices
│   ├── main.py                  # FastAPI app entry point & CORS
│   └── routers/
│       ├── inventory.py         # Products, categories & low-stock alerts
│       ├── finance.py           # Invoicing, POS checkout & stats
│       ├── discounts.py         # Discount CRUD & cart evaluation
│       └── ai_chat.py           # Natural language prompt chat endpoints
├── frontend/
│   └── src/app/
│       ├── models/pos.models.ts # TypeScript interfaces
│       ├── services/api.service.ts # Centralized HTTP client service
│       ├── components/
│       │   ├── pos/             # Counter reception & receipt printing
│       │   ├── inventory/       # Stock tracking & restock alerts
│       │   ├── finance/         # KPI cards & invoice history
│       │   └── discounts/       # AI chatbox, rule cards & simulator
│       ├── app.ts               # Navbar & low-stock notification pill
│       └── app.routes.ts        # Client-side routing
├── test_system.py               # End-to-end automated test suite
├── start_all.bat                # Windows 1-click launcher
└── README.md
```

