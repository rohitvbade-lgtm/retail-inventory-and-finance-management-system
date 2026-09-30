import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DiscountRule, Product
from ..schemas import (
    DiscountRuleCreate,
    DiscountRuleUpdate,
    DiscountRuleResponse,
    EvaluateCartRequest,
    EvaluatedCartResponse
)
from ..discount_engine import DeterministicDiscountEngine

router = APIRouter(prefix="/api/discounts", tags=["Discounts"])


def format_rule_response(rule: DiscountRule) -> DiscountRuleResponse:
    return DiscountRuleResponse(
        id=rule.id,
        name=rule.name,
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
        created_by=rule.created_by,
        created_at=rule.created_at,
        updated_at=rule.updated_at
    )


@router.get("", response_model=List[DiscountRuleResponse])
def get_discount_rules(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(DiscountRule)
    if active_only:
        query = query.filter(DiscountRule.is_active == True)
    rules = query.order_by(DiscountRule.id.desc()).all()
    return [format_rule_response(r) for r in rules]


@router.post("", response_model=DiscountRuleResponse, status_code=201)
def create_discount_rule(rule_in: DiscountRuleCreate, db: Session = Depends(get_db)):
    rule = DiscountRule(
        name=rule_in.name,
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
        eval_datetime=eval_dt
    )

    return result

