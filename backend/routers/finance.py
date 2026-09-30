import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import Invoice, InvoiceItem, Product, DiscountRule
from ..schemas import (
    CreateInvoiceRequest,
    InvoiceResponse,
    EvaluateCartRequest,
    EvaluatedCartResponse,
    DashboardStats
)
from ..discount_engine import DeterministicDiscountEngine

router = APIRouter(prefix="/api/finance", tags=["Finance & POS"])


def generate_invoice_number(db: Session) -> str:
    today_str = datetime.now().strftime("%Y%m%d")
    count_today = db.query(Invoice).filter(Invoice.invoice_number.like(f"INV-{today_str}-%")).count()
    return f"INV-{today_str}-{(count_today + 1):04d}"


@router.post("/preview", response_model=EvaluatedCartResponse)
def preview_invoice(payload: EvaluateCartRequest, db: Session = Depends(get_db)):
    """Preview calculations before finalizing checkout."""
    if not payload.items:
        return EvaluatedCartResponse(
            subtotal=0.0,
            total_discount=0.0,
            tax=0.0,
            total=0.0,
            line_items=[],
            applied_discounts=[]
        )

    product_ids = [it.product_id for it in payload.items]
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    products_map = {p.id: p for p in products}
    active_rules = db.query(DiscountRule).filter(DiscountRule.is_active == True).all()

    eval_dt = None
    if payload.simulated_date_iso:
        try:
            eval_dt = datetime.fromisoformat(payload.simulated_date_iso)
        except Exception:
            pass

    cart_inputs = [{"product_id": it.product_id, "quantity": it.quantity} for it in payload.items]
    return DeterministicDiscountEngine.evaluate_cart(
        products_map=products_map,
        cart_items_input=cart_inputs,
        active_rules=active_rules,
        eval_datetime=eval_dt
    )


@router.post("/checkout", response_model=InvoiceResponse, status_code=201)
def create_invoice(payload: CreateInvoiceRequest, db: Session = Depends(get_db)):
    """
    Finalize sale at the counter:
    1. Validates stock availability.
    2. Runs deterministic discount engine.
    3. Deducts stock from inventory.
    4. Creates invoice & invoice items records.
    """
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cart is empty. Please add items to checkout.")

    # 1. Fetch products & check stock
    product_ids = [it.product_id for it in payload.items]
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    products_map = {p.id: p for p in products}

    for item in payload.items:
        prod = products_map.get(item.product_id)
        if not prod:
            raise HTTPException(status_code=404, detail=f"Product ID {item.product_id} not found.")
        if prod.quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for '{prod.name}'. In stock: {prod.quantity}, Requested: {item.quantity}"
            )

    # 2. Evaluate discounts
    active_rules = db.query(DiscountRule).filter(DiscountRule.is_active == True).all()
    eval_dt = None
    if payload.simulated_date_iso:
        try:
            eval_dt = datetime.fromisoformat(payload.simulated_date_iso)
        except Exception:
            pass

    cart_inputs = [{"product_id": it.product_id, "quantity": it.quantity} for it in payload.items]
    calc_result = DeterministicDiscountEngine.evaluate_cart(
        products_map=products_map,
        cart_items_input=cart_inputs,
        active_rules=active_rules,
        eval_datetime=eval_dt
    )

    # 3. Create Invoice Record
    inv_number = generate_invoice_number(db)
    invoice = Invoice(
        invoice_number=inv_number,
        customer_name=payload.customer_name or "Walk-in Customer",
        customer_phone=payload.customer_phone,
        customer_email=payload.customer_email,
        subtotal=calc_result["subtotal"],
        discount_total=calc_result["total_discount"],
        tax=calc_result["tax"],
        total=calc_result["total"],
        payment_method=payload.payment_method or "Cash",
        notes=payload.notes,
        discount_breakdown=json.dumps(calc_result["applied_discounts"])
    )
    db.add(invoice)
    db.flush()

    # 4. Deduct Inventory & Create Invoice Items
    for evaluated_item in calc_result["line_items"]:
        prod = products_map[evaluated_item["product_id"]]
        # deduct quantity
        prod.quantity = max(0, prod.quantity - evaluated_item["quantity"])

        inv_item = InvoiceItem(
            invoice_id=invoice.id,
            product_id=prod.id,
            product_name=prod.name,
            category=prod.category,
            unit_price=evaluated_item["unit_price"],
            quantity=evaluated_item["quantity"],
            item_subtotal=evaluated_item["item_subtotal"],
            discount_amount=evaluated_item["discount_amount"],
            item_total=evaluated_item["final_item_total"],
            applied_discount_name=evaluated_item["applied_discount_name"]
        )
        db.add(inv_item)

    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/invoices", response_model=List[InvoiceResponse])
def get_invoices(
    search: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(Invoice)
    if search:
        s = f"%{search}%"
        query = query.filter(
            (Invoice.invoice_number.ilike(s)) |
            (Invoice.customer_name.ilike(s)) |
            (Invoice.customer_phone.ilike(s))
        )
    invoices = query.order_by(Invoice.id.desc()).limit(limit).all()
    return invoices


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    total_products = len(products)
    low_stock_count = sum(1 for p in products if p.is_low_stock)

    invoices = db.query(Invoice).all()
    total_invoices = len(invoices)
    total_revenue = sum(inv.total for inv in invoices)
    total_discounts_given = sum(inv.discount_total for inv in invoices)

    active_discounts_count = db.query(DiscountRule).filter(DiscountRule.is_active == True).count()

    return DashboardStats(
        total_products=total_products,
        low_stock_count=low_stock_count,
        total_revenue=round(total_revenue, 2),
        total_invoices=total_invoices,
        total_discounts_given=round(total_discounts_given, 2),
        active_discounts_count=active_discounts_count
    )

