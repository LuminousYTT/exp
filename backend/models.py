from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from db import Base

class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    batch_code = Column(String(120), nullable=False)
    supplier = Column(String(120), nullable=False)
    inspection_result = Column(String(50), nullable=False)
    stock_qty = Column(Integer, nullable=False, default=0)
    qr_token = Column(String(64), unique=True, nullable=False)
    extra = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Personnel(Base):
    __tablename__ = "personnel"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    employee_id = Column(String(120), unique=True, nullable=False)
    role = Column(String(120), nullable=False)
    allowed_operations = Column(Text, nullable=True)
    qr_token = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    status = Column(String(50), nullable=False, default="WIP")
    final_inspection = Column(String(50), nullable=True)
    linked_materials = Column(Text, nullable=True)
    process_data = Column(Text, nullable=True)
    qr_token = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
