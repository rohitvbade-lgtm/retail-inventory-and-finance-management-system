import os
import re
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from dotenv import load_dotenv

load_dotenv()

from .models import DiscountRule, Product, ChatMessage

# Try OpenAI SDK (for Groq / OpenAI compatible endpoints)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class AIDiscountMachineService:
    """
    AI Discount Service that processes natural language prompts from the store owner,
    translates them into structured deterministic discount rules, and applies them to the system.
    Powered by OpenAI-compatible Groq API (e.g. openai/gpt-oss-20b, qwen/qwen3.8-27b).
    """

    @classmethod
    def process_prompt(
        cls,
        prompt: str,
        db: Session,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        prompt_trimmed = prompt.strip()

        # Save user message to chat history
        user_msg = ChatMessage(role="user", content=prompt_trimmed)
        db.add(user_msg)
        db.commit()

        # Gather context: existing categories & products
        categories = [c[0] for c in db.query(Product.category).distinct().all() if c[0]]
        products = db.query(Product).all()
        prod_names = [p.name for p in products]

        parsed_action = None
        effective_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
        selected_model = model or os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))

        engine_label = "Deterministic NLU"

        # 1. Try Groq via OpenAI Client
        if effective_key and OPENAI_AVAILABLE:
            try:
                parsed_action = cls._call_openai_groq(
                    prompt=prompt_trimmed,
                    api_key=effective_key,
                    base_url=base_url,
                    model_name=selected_model,
                    temperature=temperature,
                    categories=categories,
                    product_names=prod_names
                )
                if parsed_action:
                    engine_label = f"Groq ({selected_model})"
            except Exception as e:
                print(f"[AI Service] Groq LLM call failed: {e}. Falling back to deterministic NLU parser.")

        # 2. Fallback: Deterministic NLU parser (runs 100% offline)
        if not parsed_action:
            parsed_action = cls._deterministic_nlu_parser(prompt_trimmed, categories, products)
            engine_label = "Deterministic Engine"

        # 3. Execute the internal deterministic discount action
        result = cls._execute_discount_action(parsed_action, db, prompt_trimmed, engine_label)

        # Save assistant message to chat history
        assistant_msg = ChatMessage(
            role="assistant",
            content=result["reply"],
            structured_action=json.dumps(result.get("created_discount") or {})
        )
        db.add(assistant_msg)
        db.commit()

        return result

    @classmethod
    def _call_openai_groq(
        cls,
        prompt: str,
        api_key: str,
        base_url: str,
        model_name: str,
        temperature: float,
        categories: List[str],
        product_names: List[str]
    ) -> Optional[Dict[str, Any]]:
        client = OpenAI(api_key=api_key, base_url=base_url)

        system_instruction = f"""You are the AI Discount Engine Manager for a retail store POS.
The store owner will give you instructions to set up, adjust, or check discounts.
Available product categories: {', '.join(categories)}
Sample products: {', '.join(product_names[:15])}

You MUST return ONLY a valid JSON object matching one of these structures:

If the user wants to create or set a discount rule:
{{
  "action": "create_discount_rule",
  "name": "Concise catchy rule title (e.g., Weekend 15% off Dairy)",
  "description": "Clear human-readable description",
  "discount_type": "PERCENTAGE" or "FIXED_AMOUNT",
  "value": numeric_number,
  "applicability": "CATEGORY" or "PRODUCT" or "ENTIRE_ORDER",
  "target_categories": ["CategoryName"],
  "target_products": ["ProductName"],
  "min_order_amount": 0.0,
  "schedule_type": "ALWAYS" or "WEEKEND" or "WEEKDAY" or "DATE_RANGE",
  "start_date": "YYYY-MM-DD" or null,
  "end_date": "YYYY-MM-DD" or null
}}

If the user wants to query/show active discounts:
{{
  "action": "list_discounts"
}}

If the user wants to deactivate, clear or turn off discounts:
{{
  "action": "deactivate_discounts",
  "keyword": "weekend" or target keyword
}}
Only output the JSON object, nothing else."""

        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            response_format={"type": "json_object"}
        )

        content = completion.choices[0].message.content
        if not content:
            return None

        cleaned = content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        return json.loads(cleaned.strip())

    @classmethod
    def _deterministic_nlu_parser(
        cls,
        prompt: str,
        categories: List[str],
        products: List[Product]
    ) -> Dict[str, Any]:
        """
        Deterministic, extensible parser that extracts discount parameters from natural language.
        """
        p_lower = prompt.lower()

        # Check for listing / inquiring intent
        if any(w in p_lower for w in ["what discount", "show discount", "list discount", "active discount", "all discount"]):
            return {"action": "list_discounts"}

        # Check for deactivation intent
        if any(w in p_lower for w in ["disable", "deactivate", "turn off", "remove discount", "delete discount", "clear discount"]):
            return {"action": "deactivate_discounts", "keyword": p_lower}

        # 1. Extract discount value and type
        pct_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:%|percent)', p_lower)
        fixed_match = re.search(r'(?:\$|\bflat\s*|\b)\s*(\d+(?:\.\d+)?)\s*(?:\$|dollars?|\s*off)', p_lower)

        discount_type = "PERCENTAGE"
        value = 10.0

        if pct_match:
            discount_type = "PERCENTAGE"
            value = float(pct_match.group(1))
        elif fixed_match and not pct_match:
            val_candidate = float(fixed_match.group(1))
            if "$" in p_lower or "dollar" in p_lower or "flat" in p_lower:
                discount_type = "FIXED_AMOUNT"
                value = val_candidate

        # 2. Extract schedule type
        schedule_type = "ALWAYS"
        start_date = None
        end_date = None

        if "weekend" in p_lower or "saturday" in p_lower or "sunday" in p_lower:
            schedule_type = "WEEKEND"
        elif "weekday" in p_lower or "mon to fri" in p_lower or "monday" in p_lower:
            schedule_type = "WEEKDAY"
        elif any(w in p_lower for w in ["season", "seasonal", "october", "holiday", "until", "from", "today", "tomorrow"]):
            schedule_type = "DATE_RANGE"
            now = datetime.now()
            start_date = now.strftime("%Y-%m-%d")
            if "until tomorrow" in p_lower:
                end_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
            elif "week" in p_lower:
                end_date = (now + timedelta(days=7)).strftime("%Y-%m-%d")
            elif "month" in p_lower or "season" in p_lower:
                end_date = (now + timedelta(days=30)).strftime("%Y-%m-%d")
            else:
                end_date = (now + timedelta(days=14)).strftime("%Y-%m-%d")

        # 3. Extract minimum spend
        min_order_amount = 0.0
        min_match = re.search(r'(?:orders?\s*(?:over|above|exceeding|greater than|min|minimum(?:\s*of)?)|spend(?:\s*over|\s*above)?)\s*\$?(\d+(?:\.\d+)?)', p_lower)
        if min_match:
            min_order_amount = float(min_match.group(1))

        # 4. Extract scope (Category vs Product vs Entire Order)
        applicability = "ENTIRE_ORDER"
        target_categories = []
        target_products = []

        for cat in categories:
            if cat.lower() in p_lower or (cat.lower() + "s") in p_lower:
                applicability = "CATEGORY"
                target_categories.append(cat)

        if not target_categories:
            for p in products:
                if p.name.lower() in p_lower:
                    applicability = "PRODUCT"
                    target_products.append(p.name)

        name_parts = []
        if schedule_type == "WEEKEND":
            name_parts.append("Weekend Special")
        elif schedule_type == "WEEKDAY":
            name_parts.append("Weekday Rush")
        elif schedule_type == "DATE_RANGE":
            name_parts.append("Seasonal Promo")
        else:
            name_parts.append("Store Discount")

        unit = "%" if discount_type == "PERCENTAGE" else "$"
        name_parts.append(f"{value:g}{unit} Off")

        if target_categories:
            name_parts.append(f"on {', '.join(target_categories)}")
        elif target_products:
            name_parts.append(f"on {', '.join(target_products)}")
        else:
            name_parts.append("Entire Order")

        name = " - ".join(name_parts)
        description = f"AI Generated: {value:g}{unit} off ({applicability.lower()}) with schedule {schedule_type}"
        if min_order_amount > 0:
            description += f" on orders above ${min_order_amount:g}"

        return {
            "action": "create_discount_rule",
            "name": name,
            "description": description,
            "discount_type": discount_type,
            "value": value,
            "applicability": applicability,
            "target_categories": target_categories,
            "target_products": target_products,
            "min_order_amount": min_order_amount,
            "schedule_type": schedule_type,
            "start_date": start_date,
            "end_date": end_date
        }

    @classmethod
    def _execute_discount_action(
        cls,
        action_data: Dict[str, Any],
        db: Session,
        original_prompt: str,
        engine_label: str
    ) -> Dict[str, Any]:
        action = action_data.get("action", "create_discount_rule")

        if action == "list_discounts":
            active_rules = db.query(DiscountRule).filter(DiscountRule.is_active == True).all()
            if not active_rules:
                reply = f"[{engine_label}]\nThere are currently no active discount rules in the system. Ask me to create one anytime!"
            else:
                rules_summary = "\n".join([
                    f"* **{r.name}**: {r.value}{'%' if r.discount_type == 'PERCENTAGE' else '$'} off ({r.applicability}) [{r.schedule_type}]"
                    for r in active_rules
                ])
                reply = f"[{engine_label}]\nHere are the currently active discount rules ({len(active_rules)} total):\n{rules_summary}"

            return {
                "reply": reply,
                "action_type": "LISTED_DISCOUNTS",
                "active_discounts": [cls._rule_to_dict(r) for r in active_rules]
            }

        elif action == "deactivate_discounts":
            keyword = (action_data.get("keyword") or "").lower()
            rules = db.query(DiscountRule).filter(DiscountRule.is_active == True).all()
            deactivated = []
            for r in rules:
                if any(w in r.name.lower() or w in (r.schedule_type or "").lower() for w in ["weekend", "weekday", "dairy", "beverage", "clear", "all"]):
                    r.is_active = False
                    deactivated.append(r.name)

            if not deactivated and ("all" in keyword or "clear" in keyword or "remove" in keyword):
                for r in rules:
                    r.is_active = False
                    deactivated.append(r.name)

            db.commit()
            if deactivated:
                reply = f"[{engine_label}]\nDeactivated {len(deactivated)} discount rule(s): {', '.join(deactivated)}."
            else:
                reply = f"[{engine_label}]\nNo matching active discount rules were found to deactivate."

            return {
                "reply": reply,
                "action_type": "TOGGLED_DISCOUNT"
            }

        # Generate memorable promo code candidate
        cat_prefix = ""
        target_cats = action_data.get("target_categories") or []
        target_prods = action_data.get("target_products") or []
        if target_cats:
            cat_prefix = "".join(c for c in target_cats[0] if c.isalnum())[:5].upper()
        elif action_data.get("schedule_type") == "WEEKEND":
            cat_prefix = "WKND"
        elif action_data.get("schedule_type") == "WEEKDAY":
            cat_prefix = "WKDAY"
        else:
            cat_prefix = "SAVE"

        val_int = int(action_data.get("value", 10.0))
        generated_code = f"{cat_prefix}{val_int}"

        # Check database for existing matching rule
        existing_rules = db.query(DiscountRule).all()
        matched_existing = None

        cand_discount_type = (action_data.get("discount_type") or "PERCENTAGE").upper()
        cand_value = float(action_data.get("value", 10.0))
        cand_applicability = (action_data.get("applicability") or "ENTIRE_ORDER").upper()
        cand_schedule = (action_data.get("schedule_type") or "ALWAYS").upper()
        cand_min_spend = float(action_data.get("min_order_amount", 0.0))
        cand_cats = sorted([c.strip().lower() for c in target_cats if c.strip()])
        cand_prods = sorted([p.strip().lower() for p in target_prods if p.strip()])

        for r in existing_rules:
            r_cats = sorted([c.strip().lower() for c in r.get_target_categories() if c.strip()])
            r_prods = sorted([p.strip().lower() for p in r.get_target_products() if p.strip()])
            r_eff_code = r.get_effective_code().upper()

            same_code = (r_eff_code == generated_code.upper())
            same_type = (r.discount_type or "").upper() == cand_discount_type
            same_val = abs(float(r.value or 0) - cand_value) < 0.01
            same_app = (r.applicability or "").upper() == cand_applicability
            same_sched = (r.schedule_type or "").upper() == cand_schedule
            same_cats = (r_cats == cand_cats)
            same_prods = (r_prods == cand_prods)
            same_min = abs(float(r.min_order_amount or 0) - cand_min_spend) < 0.01

            # Match if identical terms or same code with matching value/type
            if (same_type and same_val and same_app and same_sched and same_cats and same_prods and same_min) or (same_code and same_val and same_type):
                matched_existing = r
                break

        # If identical or matching rule already exists, re-enable & update timestamp
        if matched_existing:
            matched_existing.is_active = True
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")

            # Update schedule / timestamps
            if action_data.get("end_date"):
                matched_existing.start_date = action_data.get("start_date") or today_str
                matched_existing.end_date = action_data.get("end_date")
            elif matched_existing.schedule_type == "DATE_RANGE" or any(w in original_prompt.lower() for w in ["until", "week", "season", "month", "tomorrow"]):
                matched_existing.start_date = today_str
                matched_existing.end_date = (now + timedelta(days=14)).strftime("%Y-%m-%d")
            else:
                # If rule had an old expired date, extend it
                if matched_existing.end_date and matched_existing.end_date < today_str:
                    matched_existing.end_date = (now + timedelta(days=30)).strftime("%Y-%m-%d")

            db.commit()
            db.refresh(matched_existing)

            eff_code = matched_existing.get_effective_code()
            unit = "%" if matched_existing.discount_type == "PERCENTAGE" else "$"
            scope_desc = matched_existing.applicability
            if matched_existing.applicability == "CATEGORY":
                scope_desc = f"Category: {', '.join(matched_existing.get_target_categories())}"
            elif matched_existing.applicability == "PRODUCT":
                scope_desc = f"Products: {', '.join(matched_existing.get_target_products())}"
            else:
                scope_desc = "Entire Order"

            sched_desc = {
                "ALWAYS": "Anytime / All Days",
                "WEEKEND": "Saturdays & Sundays",
                "WEEKDAY": "Mondays to Fridays",
                "DATE_RANGE": f"Active {matched_existing.start_date} to {matched_existing.end_date}"
            }.get(matched_existing.schedule_type, matched_existing.schedule_type)
            expiry_str = f"Expires on {matched_existing.end_date}" if matched_existing.end_date else f"Active on {sched_desc} (No hard expiry)"

            reply = (
                f"**[{engine_label}]**\n\n"
                f"ℹ️ **Discount Code Already Present in Database!**\n\n"
                f"I detected that rule **\"{matched_existing.name}\"** with promo code `{eff_code}` is already configured in your database.\n\n"
                f"**No duplicate was added.** As requested, I have:\n"
                f"* 🟢 **Re-enabled** the discount code (Status: **ACTIVE**)\n"
                f"* 📅 **Updated expiration timestamp**: {expiry_str}\n"
                f"* 🏷️ **Promo Code**: `{eff_code}` ({matched_existing.value:g}{unit} off, {scope_desc})\n\n"
                f"Cashiers can enter promo code `{eff_code}` at checkout, or the deterministic discount engine will apply it automatically."
            )
            return {
                "reply": reply,
                "action_type": "RE_ENABLED_DISCOUNT",
                "created_discount": cls._rule_to_dict(matched_existing)
            }

        # Otherwise, terms differ slightly -> Create new rule with unique code
        unique_code = generated_code
        suffix = 2
        while any((r.code and r.code.upper() == unique_code.upper()) for r in existing_rules):
            unique_code = f"{generated_code}_{suffix}"
            suffix += 1

        rule = DiscountRule(
            name=action_data.get("name", "Store Discount"),
            code=unique_code,
            description=action_data.get("description", original_prompt),
            discount_type=cand_discount_type,
            value=cand_value,
            applicability=cand_applicability,
            target_categories=json.dumps(action_data.get("target_categories") or []),
            target_products=json.dumps(action_data.get("target_products") or []),
            min_order_amount=cand_min_spend,
            schedule_type=cand_schedule,
            start_date=action_data.get("start_date"),
            end_date=action_data.get("end_date"),
            is_active=True,
            created_by=f"AI ({engine_label}): {original_prompt[:60]}"
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)

        unit = "%" if rule.discount_type == "PERCENTAGE" else "$"
        schedule_label = {
            "ALWAYS": "Anytime",
            "WEEKEND": "Saturdays & Sundays",
            "WEEKDAY": "Mondays to Fridays",
            "DATE_RANGE": f"Active {rule.start_date} to {rule.end_date}"
        }.get(rule.schedule_type, rule.schedule_type)

        scope_label = rule.applicability
        if rule.applicability == "CATEGORY":
            scope_label = f"Category: {', '.join(rule.get_target_categories())}"
        elif rule.applicability == "PRODUCT":
            scope_label = f"Products: {', '.join(rule.get_target_products())}"
        else:
            scope_label = "Entire Order"

        reply = (
            f"**[{engine_label}]**\n\n"
            f"Created and activated new discount rule:\n\n"
            f"**{rule.name}**\n"
            f"* **Promo Code**: `{rule.code}`\n"
            f"* **Discount**: {rule.value:g}{unit} off\n"
            f"* **Scope**: {scope_label}\n"
            f"* **Schedule**: {schedule_label}\n"
            f"{f'* **Min Spend**: ${rule.min_order_amount:g}' if rule.min_order_amount > 0 else ''}\n"
        )
        similar_rules = [r for r in existing_rules if (r.applicability == rule.applicability or (r.code and r.code.startswith(cat_prefix)))]
        if similar_rules:
            reply += f"\n*(Created as a distinct new promo code because the discount terms differ from existing codes in database.)*\n"
        reply += f"\nThe deterministic discount engine will automatically apply this to qualified invoices, or cashiers can apply code `{rule.code}`."

        return {
            "reply": reply,
            "action_type": "CREATED_DISCOUNT",
            "created_discount": cls._rule_to_dict(rule)
        }

    @staticmethod
    def _rule_to_dict(r: DiscountRule) -> Dict[str, Any]:
        return {
            "id": r.id,
            "name": r.name,
            "code": r.get_effective_code(),
            "description": r.description,
            "discount_type": r.discount_type,
            "value": r.value,
            "applicability": r.applicability,
            "target_products": r.get_target_products(),
            "target_categories": r.get_target_categories(),
            "min_order_amount": r.min_order_amount,
            "schedule_type": r.schedule_type,
            "start_date": r.start_date,
            "end_date": r.end_date,
            "is_active": r.is_active,
            "is_expired": r.is_expired,
            "status": r.status,
            "created_by": r.created_by,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
