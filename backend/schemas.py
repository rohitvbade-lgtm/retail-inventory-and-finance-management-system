from datetime import datetime
from typing import List, Optional, Any, Union
from pydantic import BaseModel, Field


# ---------------- PRODUCT SCHEMAS ----------------
class ProductBase(BaseModel):
    name: str = Field(..., example="Full Cream Milk 1L")
    sku: str = Field(..., example="MLK-001")
    category: str = Field("General", example="Dairy")
    price: float = Field(..., ge=0.0, example=3.50)
    cost_price: float = Field(0.0, ge=0.0, example=2.20)
    quantity: int = Field(0, ge=0, example=25)
    min_threshold: int = Field(5, ge=0, example=5)
    description: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = Field(None, ge=0.0)
    cost_price: Optional[float] = Field(None, ge=0.0)
    quantity: Optional[int] = Field(None, ge=0)
    min_threshold: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None


class ProductStockAdjust(BaseModel):
    quantity_delta: int = Field(..., example=10, description="Positive to add stock, negative to reduce")
    reason: Optional[str] = "Manual restock/adjustment"


class ProductResponse(ProductBase):
    id: int
    is_low_stock: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------- DISCOUNT SCHEMAS ----------------
class DiscountRuleBase(BaseModel):
    name: str = Field(..., example="Weekend 15% Off Dairy")
    description: Optional[str] = None
    discount_type: str = Field("PERCENTAGE", example="PERCENTAGE", description="PERCENTAGE or FIXED_AMOUNT")
    value: float = Field(..., ge=0.0, example=15.0)
    applicability: str = Field("CATEGORY", example="CATEGORY", description="PRODUCT, CATEGORY, or ENTIRE_ORDER")
    target_products: Optional[List[Union[str, int]]] = Field(default_factory=list)
    target_categories: Optional[List[str]] = Field(default_factory=list)
    min_order_amount: float = Field(0.0, ge=0.0)
    schedule_type: str = Field("WEEKEND", example="WEEKEND", description="ALWAYS, WEEKEND, WEEKDAY, DATE_RANGE")
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None    # YYYY-MM-DD
    is_active: bool = True


class DiscountRuleCreate(DiscountRuleBase):
    created_by: Optional[str] = "Manual"


class DiscountRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    discount_type: Optional[str] = None
    value: Optional[float] = None
    applicability: Optional[str] = None
    target_products: Optional[List[Union[str, int]]] = None
    target_categories: Optional[List[str]] = None
    min_order_amount: Optional[float] = None
    schedule_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: Optional[bool] = None


class DiscountRuleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    discount_type: str
    value: float
    applicability: str
    target_products: List[Any] = []
    target_categories: List[str] = []
    min_order_amount: float
    schedule_type: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: bool
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------- POS & INVOICE SCHEMAS ----------------
class CartItemInput(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)


class EvaluateCartRequest(BaseModel):
    items: List[CartItemInput]
    simulated_date_iso: Optional[str] = None  # Optional override to simulate weekend/weekday/season


class AppliedDiscountDetail(BaseModel):
    rule_id: int
    rule_name: str
    description: Optional[str] = None
    discount_amount: float
    applicability: str
    applied_to: str


class EvaluatedCartItem(BaseModel):
    product_id: int
    name: str
    category: str
    unit_price: float
    quantity: int
    item_subtotal: float
    discount_amount: float
    final_item_total: float
    applied_discount_name: Optional[str] = None


class EvaluatedCartResponse(BaseModel):
    subtotal: float
    total_discount: float
    tax: float
    total: float
    line_items: List[EvaluatedCartItem]
    applied_discounts: List[AppliedDiscountDetail]


class CreateInvoiceRequest(BaseModel):
    customer_name: Optional[str] = "Walk-in Customer"
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    items: List[CartItemInput]
    payment_method: str = "Cash"
    notes: Optional[str] = None
    simulated_date_iso: Optional[str] = None


class InvoiceItemResponse(BaseModel):
    id: int
    product_id: Optional[int]
    product_name: str
    category: Optional[str]
    unit_price: float
    quantity: int
    item_subtotal: float
    discount_amount: float
    item_total: float
    applied_discount_name: Optional[str] = None

    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    customer_name: str
    customer_phone: Optional[str]
    customer_email: Optional[str]
    subtotal: float
    discount_total: float
    tax: float
    total: float
    payment_method: str
    notes: Optional[str]
    discount_breakdown: Optional[str]
    created_at: datetime
    items: List[InvoiceItemResponse] = []

    class Config:
        from_attributes = True


# ---------------- AI CHAT SCHEMAS ----------------
class ChatPromptRequest(BaseModel):
    message: str
    api_key: Optional[str] = None
    model: Optional[str] = "qwen-2.5-32b"


class ChatPromptResponse(BaseModel):
    reply: str
    action_type: str  # "CREATED_DISCOUNT", "LISTED_DISCOUNTS", "TOGGLED_DISCOUNT", "EXPLAINED", "ERROR"
    created_discount: Optional[DiscountRuleResponse] = None
    active_discounts: Optional[List[DiscountRuleResponse]] = None


# ---------------- DASHBOARD SCHEMAS ----------------
class DashboardStats(BaseModel):
    total_products: int
    low_stock_count: int
    total_revenue: float
    total_invoices: int
    total_discounts_given: float
    active_discounts_count: int

