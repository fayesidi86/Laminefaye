from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Table, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base

# Association table for many-to-many between orders and products (order items)
order_items = Table(
    "order_items",
    Base.metadata,
    Column("order_id", ForeignKey("orders.id"), primary_key=True),
    Column("product_id", ForeignKey("products.id"), primary_key=True),
    Column("quantity", Integer, nullable=False, default=1),
    Column("unit_price", Float, nullable=False),
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="user")  # admin / user
    created_at = Column(DateTime, default=datetime.utcnow)

    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")

class Category(Base):
    __tablename__ = "categories"
    id = Column(String(60), primary_key=True)
    name = Column(String(80), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "products"
    id = Column(String(120), primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    discount_percent = Column(Float, default=0.0)
    stock = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)
    likes = Column(Integer, default=0)
    category_id = Column(String(60), ForeignKey("categories.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    orders = relationship("Order", secondary=order_items, back_populates="products")

class ProductImage(Base):
    __tablename__ = "product_images"
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(2048), nullable=False)
    alt_text = Column(String(255), nullable=True)
    order_idx = Column(Integer, default=0)
    product_id = Column(String(120), ForeignKey("products.id"), nullable=False)

    product = relationship("Product", back_populates="images")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(String(30), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="orders")
    products = relationship("Product", secondary=order_items, back_populates="orders")

class Favorite(Base):
    __tablename__ = "favorites"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    product_id = Column(String(120), ForeignKey("products.id"), primary_key=True)
    added_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="favorites")
    product = relationship("Product")

class Like(Base):
    __tablename__ = "likes"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    product_id = Column(String(120), ForeignKey("products.id"), primary_key=True)
    liked_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="likes")
    product = relationship("Product")
