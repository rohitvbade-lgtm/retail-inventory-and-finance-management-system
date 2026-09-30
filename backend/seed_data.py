import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .models import Product, DiscountRule, Invoice, InvoiceItem, ChatMessage
from .database import engine, Base, SessionLocal


def seed_database():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # Check if already seeded
        if db.query(Product).count() > 0:
            print("[Seed] Database already contains products. Skipping seed.")
            return

        print("[Seed] Seeding sample products, discounts, and invoices...")

        sample_products = [
            Product(
                name="Organic Whole Milk 1L",
                sku="MLK-001",
                category="Dairy",
                price=3.99,
                cost_price=2.40,
                quantity=18,
                min_threshold=5,
                description="Fresh organic whole milk from local dairy"
            ),
            Product(
                name="Greek Yogurt 500g",
                sku="YOG-002",
                category="Dairy",
                price=4.50,
                cost_price=2.80,
                quantity=3,  # LOW STOCK (<= 5)
                min_threshold=5,
                description="Plain Greek strained whole milk yogurt"
            ),
            Product(
                name="Artisan Sourdough Loaf",
                sku="BAK-001",
                category="Bakery",
                price=5.25,
                cost_price=2.10,
                quantity=12,
                min_threshold=4,
                description="Naturally fermented crusty sourdough loaf"
            ),
            Product(
                name="Fresh Croissant (Pack of 2)",
                sku="BAK-002",
                category="Bakery",
                price=3.50,
                cost_price=1.60,
                quantity=2,  # LOW STOCK (<= 5)
                min_threshold=5,
                description="Golden flaky French butter croissants"
            ),
            Product(
                name="Cold Brew Arabica Coffee 330ml",
                sku="BEV-001",
                category="Beverages",
                price=4.20,
                cost_price=1.80,
                quantity=24,
                min_threshold=8,
                description="Smooth single-origin cold brewed iced coffee"
            ),
            Product(
                name="Sparkling Mineral Water 750ml",
                sku="BEV-002",
                category="Beverages",
                price=2.75,
                cost_price=1.10,
                quantity=30,
                min_threshold=6,
                description="Crisp Italian natural sparkling mineral water"
            ),
            Product(
                name="Organic Honeycrisp Apples (1kg)",
                sku="PRO-001",
                category="Produce",
                price=5.99,
                cost_price=3.50,
                quantity=4,  # LOW STOCK (<= 6)
                min_threshold=6,
                description="Crisp sweet orchard-picked organic apples"
            ),
            Product(
                name="Sea Salt Kettle Potato Chips 150g",
                sku="SNK-001",
                category="Snacks",
                price=3.40,
                cost_price=1.50,
                quantity=15,
                min_threshold=5,
                description="Hand-cooked potato chips with natural sea salt"
            ),
            Product(
                name="Dark Chocolate Bar 85% 100g",
                sku="SNK-002",
                category="Snacks",
                price=4.10,
                cost_price=2.00,
                quantity=1,  # CRITICAL LOW STOCK
                min_threshold=5,
                description="Fairtrade dark chocolate with Madagascar cocoa"
            ),
            Product(
                name="Organic Free-Range Eggs (Dozen)",
                sku="DAI-003",
                category="Dairy",
                price=6.50,
                cost_price=4.00,
                quantity=14,
                min_threshold=5,
                description="Grade A large organic brown pasture eggs"
            )
        ]

        db.add_all(sample_products)
        db.commit()

        # Seed sample discount rules
        sample_discounts = [
            DiscountRule(
                name="Weekend Dairy Blast",
                description="15% off all Dairy products on weekends (Sat-Sun)",
                discount_type="PERCENTAGE",
                value=15.0,
                applicability="CATEGORY",
                target_categories=json.dumps(["Dairy"]),
                target_products=json.dumps([]),
                min_order_amount=0.0,
                schedule_type="WEEKEND",
                is_active=True,
                created_by="Seed Demo"
            ),
            DiscountRule(
                name="Weekday Coffee & Snack Rush",
                description="10% off Beverages and Snacks from Mon to Fri",
                discount_type="PERCENTAGE",
                value=10.0,
                applicability="CATEGORY",
                target_categories=json.dumps(["Beverages", "Snacks"]),
                target_products=json.dumps([]),
                min_order_amount=0.0,
                schedule_type="WEEKDAY",
                is_active=True,
                created_by="Seed Demo"
            ),
            DiscountRule(
                name="High Value Cart Special",
                description="Flat $5 off entire cart when spending $40 or more",
                discount_type="FIXED_AMOUNT",
                value=5.0,
                applicability="ENTIRE_ORDER",
                target_categories=json.dumps([]),
                target_products=json.dumps([]),
                min_order_amount=40.0,
                schedule_type="ALWAYS",
                is_active=True,
                created_by="Seed Demo"
            )
        ]
        db.add_all(sample_discounts)
        db.commit()

        # Seed initial greeting in Chat
        initial_chat = ChatMessage(
            role="assistant",
            content="Hello! I am your AI Discount Machine. You can prompt me to create any discount for your shop—e.g., *'Give 15% discount on all dairy products this weekend'* or *'Apply $5 off on orders over $50 on weekdays'*. I will convert your instructions into deterministic discount rules and apply them automatically to customer invoices!",
            structured_action=None
        )
        db.add(initial_chat)
        db.commit()

        print("[Seed] Seeding completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"[Seed] Error seeding database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

