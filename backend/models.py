from datetime import datetime, timezone
import json
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(100), nullable=False, default="General", index=True)
    price = Column(Float, nullable=False, default=0.0)
    cost_price = Column(Float, nullable=False, default=0.0)
    quantity = Column(Integer, nullable=False, default=0)
    min_threshold = Column(Integer, nullable=False, default=5)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    @property
    def is_low_stock(self) -> bool:
        return self.quantity <= self.min_threshold


class DiscountRule(Base):
    __tablename__ = "discount_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # "PERCENTAGE" or "FIXED_AMOUNT"
    discount_type = Column(String(50), nullable=False, default="PERCENTAGE")
    value = Column(Float, nullable=False, default=0.0)
    
    # "PRODUCT", "CATEGORY", "ENTIRE_ORDER"
    applicability = Column(String(50), nullable=False, default="ENTIRE_ORDER")
    
    # Stored as JSON strings: e.g. ["Dairy", "Beverages"] or [1, 2]
    target_products = Column(Text, nullable=True, default="[]")
    target_categories = Column(Text, nullable=True, default="[]")
    
    min_order_amount = Column(Float, nullable=False, default=0.0)
    
    # "ALWAYS", "WEEKEND", "WEEKDAY", "DATE_RANGE"
    schedule_type = Column(String(50), nullable=False, default="ALWAYS")
    start_date = Column(String(50), nullable=True)  # YYYY-MM-DD
    end_date = Column(String(50), nullable=True)    # YYYY-MM-DD
    
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(String(200), nullable=True, default="System")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    def get_target_products(self):
        try:
            return json.loads(self.target_products or "[]")
        except Exception:
            return []

    def get_target_categories(self):
        try:
            return json.loads(self.target_categories or "[]")
        except Exception:
            return []


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(100), unique=True, nullable=False, index=True)
    customer_name = Column(String(200), nullable=False, default="Walk-in Customer")
    customer_phone = Column(String(50), nullable=True)
    customer_email = Column(String(100), nullable=True)
    
    subtotal = Column(Float, nullable=False, default=0.0)
    discount_total = Column(Float, nullable=False, default=0.0)
    tax = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False, default=0.0)
    
    payment_method = Column(String(50), nullable=False, default="Cash")
    notes = Column(Text, nullable=True)
    discount_breakdown = Column(Text, nullable=True, default="[]")  # JSON summary
    
    created_at = Column(DateTime, default=utc_now)

    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    product_name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=True)
    unit_price = Column(Float, nullable=False, default=0.0)
    quantity = Column(Integer, nullable=False, default=1)
    item_subtotal = Column(Float, nullable=False, default=0.0)
    discount_amount = Column(Float, nullable=False, default=0.0)
    item_total = Column(Float, nullable=False, default=0.0)
    applied_discount_name = Column(String(200), nullable=True)

    invoice = relationship("Invoice", back_populates="items")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    structured_action = Column(Text, nullable=True)  # JSON representation of action/discount rule created
    created_at = Column(DateTime, default=utc_now)

