import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def run_tests():
    print("==================================================")
    print("STARTING FULL-STACK SYSTEM VERIFICATION (GROQ QWEN)")
    print("==================================================")

    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[OK] Health check passed")

    # 2. Check initial inventory & low-stock alerts
    res = client.get("/api/products")
    assert res.status_code == 200
    products = res.json()
    print(f"[OK] Inventory loaded: {len(products)} products found")

    res = client.get("/api/products/low-stock/alerts")
    assert res.status_code == 200
    alerts = res.json()
    print(f"[OK] Low-stock alerts functional: {len(alerts)} items currently below threshold:")
    for a in alerts:
        print(f"   * {a['name']} (Stock: {a['quantity']} / Min: {a['min_threshold']})")
    assert len(alerts) > 0, "Expected at least 1 low-stock product from seed"

    # 3. Test AI Discount Machine with natural language prompt
    prompt = "Give 15% discount on all dairy products this weekend"
    print(f"\n--- Testing AI Discount Machine Prompt (Groq/Qwen): '{prompt}' ---")
    res = client.post("/api/ai/chat", json={"message": prompt, "model": "qwen-2.5-32b"})
    assert res.status_code == 200
    chat_data = res.json()
    print(f"AI Assistant Reply:\n{chat_data['reply']}\n")
    assert chat_data["action_type"] == "CREATED_DISCOUNT"
    created_rule = chat_data["created_discount"]
    assert created_rule is not None
    assert created_rule["value"] == 15.0
    assert created_rule["schedule_type"] == "WEEKEND"
    print(f"[OK] Successfully created rule: ID={created_rule['id']}, Value={created_rule['value']}%, Schedule={created_rule['schedule_type']}")

    # 4. Test Second AI Prompt: Min spend weekday rule
    prompt2 = "Apply flat $5 discount on orders over $40 on weekdays"
    print(f"\n--- Testing AI Discount Machine Prompt: '{prompt2}' ---")
    res = client.post("/api/ai/chat", json={"message": prompt2, "model": "qwen-2.5-32b"})
    assert res.status_code == 200
    chat_data2 = res.json()
    created_rule2 = chat_data2["created_discount"]
    print(f"[OK] Successfully created rule: '{created_rule2['name']}' (Min Spend: ${created_rule2['min_order_amount']})")

    # 5. Deterministic Discount Engine Evaluation
    dairy_prod = next(p for p in products if p["category"] == "Dairy")
    snack_prod = next(p for p in products if p["category"] == "Snacks")

    # Simulate on a Saturday (Weekend)
    sim_weekend = "2026-10-03T14:00:00"  # Oct 3, 2026 is Saturday
    preview_res = client.post("/api/discounts/evaluate", json={
        "items": [
            {"product_id": dairy_prod["id"], "quantity": 2},
            {"product_id": snack_prod["id"], "quantity": 1}
        ],
        "simulated_date_iso": sim_weekend
    })
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    print(f"\n[OK] Weekend Cart Evaluation Preview:")
    print(f"   Subtotal: ${preview_data['subtotal']:.2f}")
    print(f"   Total Discount: -${preview_data['total_discount']:.2f}")
    print(f"   Total Payable: ${preview_data['total']:.2f}")
    print(f"   Applied Discounts count: {len(preview_data['applied_discounts'])}")
    for d in preview_data['applied_discounts']:
        print(f"     -> {d['rule_name']}: -${d['discount_amount']:.2f} ({d['applied_to']})")

    assert preview_data['total_discount'] > 0, "Expected weekend discount to apply to dairy!"

    # 6. Counter Invoicing (Checkout) & Automatic Inventory Deduction
    # Pick a product with sufficient stock
    checkout_prod = next(p for p in products if p["quantity"] >= 2)
    initial_stock = checkout_prod["quantity"]
    print(f"\n--- Testing Counter Checkout (POS Sale) ---")
    print(f"Product '{checkout_prod['name']}' stock before checkout: {initial_stock}")

    checkout_res = client.post("/api/finance/checkout", json={
        "customer_name": "Alice Green",
        "customer_phone": "555-0199",
        "payment_method": "Cash",
        "items": [
            {"product_id": checkout_prod["id"], "quantity": 2}
        ],
        "simulated_date_iso": sim_weekend
    })
    assert checkout_res.status_code == 201
    invoice = checkout_res.json()
    print(f"[OK] Invoice Generated: {invoice['invoice_number']}")
    print(f"   Customer: {invoice['customer_name']}")
    print(f"   Subtotal: ${invoice['subtotal']:.2f}, Discount: -${invoice['discount_total']:.2f}, Total: ${invoice['total']:.2f}")
    print(f"   Items count: {len(invoice['items'])}")

    # Check stock deduction
    refreshed_prod = client.get(f"/api/products/{checkout_prod['id']}").json()
    print(f"Product '{checkout_prod['name']}' stock after checkout: {refreshed_prod['quantity']}")
    assert refreshed_prod["quantity"] == initial_stock - 2, "Stock quantity should be reduced by 2"

    # 7. Check Dashboard Stats
    stats = client.get("/api/finance/dashboard/stats").json()
    print(f"\n[OK] Financial Dashboard Stats:")
    print(f"   Total Revenue: ${stats['total_revenue']:.2f}")
    print(f"   Total Invoices: {stats['total_invoices']}")
    print(f"   Total Discounts Given: ${stats['total_discounts_given']:.2f}")
    print(f"   Low Stock Products Count: {stats['low_stock_count']}")

    print("\n==================================================")
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
