from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
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
    parent_token = Column(String(64), nullable=True)
    qr_token = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Process(Base):
    __tablename__ = "processes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    sequence = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(120), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="worker")
    permissions = Column(Text, nullable=True)  # JSON string of permission codes
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(120), unique=True, nullable=False)
    product_name = Column(String(120), nullable=False)
    material_batch = Column(String(120), nullable=True)
    plan_qty = Column(Integer, nullable=False, default=0)
    line = Column(String(120), nullable=True)
    status = Column(String(50), nullable=False, default="待执行")
    planned_start = Column(String(50), nullable=True)
    planned_end = Column(String(50), nullable=True)
    qr_token = Column(String(64), unique=True, nullable=False)
    completion_qr_token = Column(String(64), unique=True, nullable=True)
    created_by = Column(String(120), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkOrderProgress(Base):
    __tablename__ = "work_order_progress"

    id = Column(Integer, primary_key=True, index=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False)
    actual_qty = Column(Integer, nullable=False, default=0)
    defect_qty = Column(Integer, nullable=False, default=0)
    operator_id = Column(Integer, ForeignKey("personnel.id"), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkOrderException(Base):
    __tablename__ = "work_order_exceptions"

    id = Column(Integer, primary_key=True, index=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False)
    exception_type = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    action = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="open")
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class InspectionRecord(Base):
    __tablename__ = "inspection_records"

    id = Column(Integer, primary_key=True, index=True)
    object_type = Column(String(50), nullable=False)  # material/process/product/workorder
    object_token = Column(String(64), nullable=True)
    result = Column(String(50), nullable=False)
    inspector = Column(String(120), nullable=True)
    items = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MaterialReceipt(Base):
    __tablename__ = "material_receipts"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    location = Column(String(120), nullable=True)
    qty = Column(Integer, nullable=False, default=0)
    operator = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProductInventoryMove(Base):
    __tablename__ = "product_inventory_moves"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    product_name = Column(String(120), nullable=False)
    direction = Column(String(20), nullable=False)  # in/out
    qty = Column(Integer, nullable=False, default=0)
    location = Column(String(120), nullable=True)
    order_code = Column(String(120), nullable=True)
    customer = Column(String(120), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SemiProduct(Base):
    __tablename__ = "semi_products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    stage = Column(String(50), nullable=False)  # juice / ferment
    stock_qty = Column(Integer, nullable=False, default=0)
    parent_token = Column(String(64), nullable=True)  # upstream material/semi/product token
    qr_token = Column(String(64), unique=True, nullable=False)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class StocktakeRecord(Base):
    __tablename__ = "stocktake_records"

    id = Column(Integer, primary_key=True, index=True)
    item_type = Column(String(50), nullable=False)  # material/product
    item_id = Column(Integer, nullable=False)
    real_qty = Column(Integer, nullable=False, default=0)
    delta = Column(Integer, nullable=False, default=0)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
