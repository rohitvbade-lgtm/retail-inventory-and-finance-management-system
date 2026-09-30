from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..models import Product
from ..schemas import ProductCreate, ProductUpdate, ProductResponse, ProductStockAdjust

router = APIRouter(prefix="/api/products", tags=["Inventory"])


@router.get("", response_model=List[ProductResponse])
def get_products(
    search: Optional[str] = None,
    category: Optional[str] = None,
    low_stock_only: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(Product)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(or_(Product.name.ilike(search_filter), Product.sku.ilike(search_filter)))
    
    if category and category != "All":
        query = query.filter(Product.category == category)
        
    products = query.order_by(Product.name.asc()).all()
    
    if low_stock_only:
        products = [p for p in products if p.is_low_stock]
        
    return products


@router.get("/low-stock/alerts", response_model=List[ProductResponse])
def get_low_stock_alerts(db: Session = Depends(get_db)):
    """Retrieve all products that have dropped below or equal to their min_threshold."""
    all_products = db.query(Product).all()
    low_stock = [p for p in all_products if p.is_low_stock]
    return low_stock


@router.get("/categories", response_model=List[str])
def get_categories(db: Session = Depends(get_db)):
    cats = db.query(Product.category).distinct().all()
    categories = sorted([c[0] for c in cats if c[0]])
    return categories


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    existing = db.query(Product).filter(Product.sku == product_in.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Product with SKU '{product_in.sku}' already exists.")
        
    product = Product(
        name=product_in.name,
        sku=product_in.sku,
        category=product_in.category or "General",
        price=product_in.price,
        cost_price=product_in.cost_price,
        quantity=product_in.quantity,
        min_threshold=product_in.min_threshold,
        description=product_in.description
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product_in: ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_in.model_dump(exclude_unset=True)
    if "sku" in update_data and update_data["sku"] != product.sku:
        existing = db.query(Product).filter(Product.sku == update_data["sku"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="Another product with this SKU already exists.")

    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}/stock", response_model=ProductResponse)
def adjust_stock(product_id: int, adjust: ProductStockAdjust, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    new_quantity = product.quantity + adjust.quantity_delta
    if new_quantity < 0:
        raise HTTPException(status_code=400, detail="Cannot reduce stock below zero.")

    product.quantity = new_quantity
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    db.delete(product)
    db.commit()
    return {"message": f"Product '{product.name}' deleted successfully."}

