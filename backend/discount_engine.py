from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
import json
from .models import DiscountRule, Product


class DeterministicDiscountEngine:
    """
    Extensible, deterministic rule-based discount engine.
    Calculates discounts strictly according to active rules, schedule conditions,
    and product/category/cart scopes.
    """

    @classmethod
    def is_rule_applicable_by_schedule(cls, rule: DiscountRule, eval_datetime: datetime) -> Tuple[bool, str]:
        schedule = (rule.schedule_type or "ALWAYS").upper()
        
        # 0 = Monday, 6 = Sunday
        weekday = eval_datetime.weekday()
        
        if schedule == "ALWAYS":
            return True, "Applies at all times"
        
        elif schedule == "WEEKEND":
            # Saturday (5) or Sunday (6)
            if weekday in [5, 6]:
                return True, "Weekend rule matched (Sat/Sun)"
            return False, f"Rule is only valid on Weekends (Current day: {eval_datetime.strftime('%A')})"
        
        elif schedule == "WEEKDAY":
            # Monday (0) to Friday (4)
            if weekday in [0, 1, 2, 3, 4]:
                return True, "Weekday rule matched (Mon-Fri)"
            return False, f"Rule is only valid on Weekdays (Current day: {eval_datetime.strftime('%A')})"
        
        elif schedule == "DATE_RANGE":
            eval_date_str = eval_datetime.strftime("%Y-%m-%d")
            if rule.start_date and eval_date_str < rule.start_date:
                return False, f"Rule starts on {rule.start_date}"
            if rule.end_date and eval_date_str > rule.end_date:
                return False, f"Rule expired on {rule.end_date}"
            return True, f"Date within active range ({rule.start_date} to {rule.end_date})"
        
        return False, f"Unknown schedule type: {schedule}"

    @classmethod
    def evaluate_cart(
        cls,
        products_map: Dict[int, Product],
        cart_items_input: List[Dict[str, Any]],
        active_rules: List[DiscountRule],
        eval_datetime: Optional[datetime] = None,
        promo_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Pure deterministic calculation:
        1. Validates and prepares cart line items.
        2. Filters rules applicable to current time/date and minimum order threshold.
        3. Evaluates product-level and category-level discounts.
        4. Evaluates entire-order level discounts.
        5. Computes final subtotals, tax, and returns a detailed audit breakdown.
        """
        if eval_datetime is None:
            eval_datetime = datetime.now()

        # Step 1: Prepare cart items with base subtotal
        prepared_items = []
        gross_subtotal = 0.0

        for item in cart_items_input:
            p_id = item["product_id"]
            qty = item["quantity"]
            product = products_map.get(p_id)
            if not product:
                continue
            
            unit_price = float(product.price)
            line_subtotal = round(unit_price * qty, 2)
            gross_subtotal += line_subtotal
            
            prepared_items.append({
                "product_id": product.id,
                "name": product.name,
                "category": product.category or "General",
                "unit_price": unit_price,
                "quantity": qty,
                "item_subtotal": line_subtotal,
                "discount_amount": 0.0,
                "final_item_total": line_subtotal,
                "applied_discount_name": None,
                "product_obj": product
            })

        gross_subtotal = round(gross_subtotal, 2)

        # Step 2: Filter active & schedule-valid rules
        qualified_rules: List[DiscountRule] = []
        for rule in active_rules:
            if not rule.is_active:
                continue
            
            is_valid_sched, _ = cls.is_rule_applicable_by_schedule(rule, eval_datetime)
            if not is_valid_sched:
                continue
            
            # Check min order amount against current cart gross subtotal
            if rule.min_order_amount and gross_subtotal < rule.min_order_amount:
                continue
            
            qualified_rules.append(rule)

        applied_discounts = []
        total_discount = 0.0

        # Step 3: Evaluate line-item level discounts (PRODUCT & CATEGORY)
        for rule in qualified_rules:
            app = (rule.applicability or "ENTIRE_ORDER").upper()
            disc_type = (rule.discount_type or "PERCENTAGE").upper()
            val = float(rule.value)

            if app == "PRODUCT":
                # Matches target products by ID or Name
                target_prods = rule.get_target_products()
                # normalize targets to string or int
                matching_items = []
                for itm in prepared_items:
                    # check match by id or name
                    if itm["product_id"] in target_prods or itm["name"] in target_prods or str(itm["product_id"]) in [str(x) for x in target_prods]:
                        matching_items.append(itm)

                if matching_items:
                    rule_discount_total = 0.0
                    for m_item in matching_items:
                        # calculate discount for this item
                        if disc_type == "PERCENTAGE":
                            # e.g., 20% off
                            item_disc = round(m_item["item_subtotal"] * (val / 100.0), 2)
                        else:
                            # Fixed amount off (capped by item subtotal)
                            item_disc = min(round(val * m_item["quantity"], 2), m_item["item_subtotal"])

                        # Avoid double-counting if an earlier rule already discounted it heavily
                        item_disc = min(item_disc, m_item["final_item_total"])
                        if item_disc > 0:
                            m_item["discount_amount"] = round(m_item["discount_amount"] + item_disc, 2)
                            m_item["final_item_total"] = round(m_item["item_subtotal"] - m_item["discount_amount"], 2)
                            m_item["applied_discount_name"] = rule.name
                            rule_discount_total += item_disc

                    rule_discount_total = round(rule_discount_total, 2)
                    if rule_discount_total > 0:
                        total_discount += rule_discount_total
                        applied_discounts.append({
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "code": rule.get_effective_code(),
                            "description": rule.description or f"{val}{'%' if disc_type == 'PERCENTAGE' else '$'} on targeted products",
                            "discount_amount": rule_discount_total,
                            "applicability": "PRODUCT",
                            "applied_to": ", ".join([it["name"] for it in matching_items])
                        })

            elif app == "CATEGORY":
                target_cats = [c.strip().lower() for c in rule.get_target_categories()]
                matching_items = [
                    itm for itm in prepared_items
                    if (itm["category"] or "").strip().lower() in target_cats
                ]

                if matching_items:
                    rule_discount_total = 0.0
                    for m_item in matching_items:
                        if disc_type == "PERCENTAGE":
                            item_disc = round(m_item["item_subtotal"] * (val / 100.0), 2)
                        else:
                            item_disc = min(round(val * m_item["quantity"], 2), m_item["item_subtotal"])

                        item_disc = min(item_disc, m_item["final_item_total"])
                        if item_disc > 0:
                            m_item["discount_amount"] = round(m_item["discount_amount"] + item_disc, 2)
                            m_item["final_item_total"] = round(m_item["item_subtotal"] - m_item["discount_amount"], 2)
                            m_item["applied_discount_name"] = rule.name
                            rule_discount_total += item_disc

                    rule_discount_total = round(rule_discount_total, 2)
                    if rule_discount_total > 0:
                        total_discount += rule_discount_total
                        applied_discounts.append({
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "code": rule.get_effective_code(),
                            "description": rule.description or f"{val}{'%' if disc_type == 'PERCENTAGE' else '$'} on {', '.join(rule.get_target_categories())}",
                            "discount_amount": rule_discount_total,
                            "applicability": "CATEGORY",
                            "applied_to": f"Category: {', '.join(rule.get_target_categories())}"
                        })

        # Step 4: Evaluate Entire-Order Level Discounts
        for rule in qualified_rules:
            app = (rule.applicability or "ENTIRE_ORDER").upper()
            disc_type = (rule.discount_type or "PERCENTAGE").upper()
            val = float(rule.value)

            if app == "ENTIRE_ORDER":
                # Compute remaining order balance
                current_cart_total = max(0.0, round(gross_subtotal - total_discount, 2))
                if current_cart_total <= 0:
                    continue

                if disc_type == "PERCENTAGE":
                    order_disc = round(gross_subtotal * (val / 100.0), 2)
                else:
                    order_disc = round(val, 2)

                order_disc = min(order_disc, current_cart_total)
                if order_disc > 0:
                    total_discount = round(total_discount + order_disc, 2)
                    applied_discounts.append({
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "code": rule.get_effective_code(),
                        "description": rule.description or f"{val}{'%' if disc_type == 'PERCENTAGE' else '$'} off entire order",
                        "discount_amount": order_disc,
                        "applicability": "ENTIRE_ORDER",
                        "applied_to": "Entire Cart"
                    })

        total_discount = min(total_discount, gross_subtotal)
        total_discount = round(total_discount, 2)

        # Check promo code resolution
        promo_code_status = None
        if promo_code:
            clean_code = promo_code.strip().upper()
            was_applied = any(
                (d.get("code") and d.get("code").upper() == clean_code) or
                clean_code in (d.get("rule_name") or "").upper()
                for d in applied_discounts
            )
            if was_applied:
                promo_code_status = "APPLIED"
            else:
                matching_rule = next(
                    (r for r in active_rules if (r.code and r.code.strip().upper() == clean_code) or r.get_effective_code() == clean_code or clean_code in r.name.upper()),
                    None
                )
                if matching_rule:
                    if matching_rule.is_expired or not matching_rule.is_active:
                        promo_code_status = "EXPIRED"
                    else:
                        promo_code_status = "NOT_APPLICABLE"
                else:
                    promo_code_status = "INVALID"

        # Remove internal objects before returning
        clean_line_items = []
        for itm in prepared_items:
            clean_line_items.append({
                "product_id": itm["product_id"],
                "name": itm["name"],
                "category": itm["category"],
                "unit_price": itm["unit_price"],
                "quantity": itm["quantity"],
                "item_subtotal": itm["item_subtotal"],
                "discount_amount": itm["discount_amount"],
                "final_item_total": itm["final_item_total"],
                "applied_discount_name": itm["applied_discount_name"]
            })

        net_total = round(gross_subtotal - total_discount, 2)
        tax = 0.0

        return {
            "subtotal": gross_subtotal,
            "total_discount": total_discount,
            "tax": tax,
            "total": round(net_total + tax, 2),
            "line_items": clean_line_items,
            "applied_discounts": applied_discounts,
            "promo_code": promo_code,
            "promo_code_status": promo_code_status
        }

