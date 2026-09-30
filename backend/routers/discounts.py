import json
import math
from datetime import datetime
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DiscountRule, Product
from ..schemas import (
    DiscountRuleCreate,
    DiscountRuleUpdate,
    DiscountRuleResponse,
    PaginatedDiscountResponse,
    EvaluateCartRequest,
    EvaluatedCartResponse
)
from ..discount_engine import DeterministicDiscountEngine

router = APIRouter(prefix="/api/discounts", tags=["Discounts"])


def format_rule_response(rule: DiscountRule) -> DiscountRuleResponse:
    return DiscountRuleResponse(
        id=rule.id,
        name=rule.name,
        code=rule.get_effective_code(),
        description=rule.description,
        discount_type=rule.discount_type,
        value=rule.value,
        applicability=rule.applicability,
        target_products=rule.get_target_products(),
        target_categories=rule.get_target_categories(),
        min_order_amount=rule.min_order_amount,
        schedule_type=rule.schedule_type,
        start_date=rule.start_date,
        end_date=rule.end_date,
        is_active=rule.is_active,
        is_expired=rule.is_expired,
        status=rule.status,
        created_by=rule.created_by,
        created_at=rule.created_at,
        updated_at=rule.updated_at
    )


@router.get("", response_model=Union[PaginatedDiscountResponse, List[DiscountRuleResponse]])
def get_discount_rules(
    active_only: bool = False,
    tab: str = Query("all", description="'active', 'expired', or 'all'"),
    search: Optional[str] = None,
    page: Optional[int] = Query(None, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    all_rules = db.query(DiscountRule).order_by(DiscountRule.id.desc()).all()
    formatted = [format_rule_response(r) for r in all_rules]

    active_count = sum(1 for r in formatted if r.status == "ACTIVE")
    expired_count = sum(1 for r in formatted if r.status in ["EXPIRED", "INACTIVE"])

    filtered = formatted
    if tab == "active" or active_only:
        filtered = [r for r in filtered if r.status == "ACTIVE"]
    elif tab == "expired":
        filtered = [r for r in filtered if r.status in ["EXPIRED", "INACTIVE"]]

    if search:
        s = search.strip().lower()
        filtered = [
            r for r in filtered
            if s in r.name.lower() or (r.code and s in r.code.lower()) or (r.description and s in r.description.lower())
        ]

    if page is not None:
        total = len(filtered)
        total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
        offset = (page - 1) * page_size
        items = filtered[offset : offset + page_size]
        return PaginatedDiscountResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            active_count=active_count,
            expired_count=expired_count
        )

    return filtered


@router.post("", response_model=DiscountRuleResponse, status_code=201)
def create_discount_rule(rule_in: DiscountRuleCreate, db: Session = Depends(get_db)):
    rule = DiscountRule(
        name=rule_in.name,
        code=rule_in.code.strip().upper() if rule_in.code and rule_in.code.strip() else None,
        description=rule_in.description,
        discount_type=rule_in.discount_type.upper(),
        value=rule_in.value,
        applicability=rule_in.applicability.upper(),
        target_products=json.dumps(rule_in.target_products or []),
        target_categories=json.dumps(rule_in.target_categories or []),
        min_order_amount=rule_in.min_order_amount,
        schedule_type=rule_in.schedule_type.upper(),
        start_date=rule_in.start_date,
        end_date=rule_in.end_date,
        is_active=rule_in.is_active,
        created_by=rule_in.created_by or "Manual"
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return format_rule_response(rule)


@router.patch("/{rule_id}/toggle", response_model=DiscountRuleResponse)
def toggle_discount_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(DiscountRule).filter(DiscountRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Discount rule not found")
        
    rule.is_active = not rule.is_active
    db.commit()
    db.refresh(rule)
    return format_rule_response(rule)


@router.delete("/{rule_id}")
def delete_discount_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(DiscountRule).filter(DiscountRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Discount rule not found")
        
    db.delete(rule)
    db.commit()
    return {"message": f"Discount rule '{rule.name}' deleted."}


@router.post("/evaluate", response_model=EvaluatedCartResponse)
def evaluate_cart_discounts(
    payload: EvaluateCartRequest,
    db: Session = Depends(get_db)
):
    """
    Deterministic Cart & Discount Simulator:
    Computes exact discounts that will be applied based on current active rules
    and an optional simulated date (for testing weekend/weekday/seasonal rules).
    """
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
    result = DeterministicDiscountEngine.evaluate_cart(
        products_map=products_map,
        cart_items_input=cart_inputs,
        active_rules=active_rules,
        eval_datetime=eval_dt,
        promo_code=payload.promo_code
    )

    return result

