from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models import Category, Product, ProductImage

router = APIRouter(prefix="/api/categories", tags=["categories"])

@router.get("/", response_model=List[Category])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Category)
def create_category(cat: Category, db: Session = Depends(get_db), token: str = Depends(...)):
    # token validation placeholder – you can plug your admin token logic here
    existing = db.query(Category).filter(Category.id == cat.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat
