import base64
import io
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import select, func
from werkzeug.security import generate_password_hash, check_password_hash

import config
from db import Base, engine, SessionLocal
from models import (
    Material,
    Personnel,
    Product,
    Process,
    User,
    WorkOrder,
    WorkOrderProgress,
    WorkOrderException,
    InspectionRecord,
    MaterialReceipt,
    ProductInventoryMove,
)

app = Flask(__name__)
CORS(app)

# Initialize database schema if missing
Base.metadata.create_all(bind=engine)


def generate_qr_base64(data: str) -> str:
    import qrcode
    from qrcode.image.pil import PilImage

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    # Use PIL image backend so we can save with format="PNG" without PyPNG issues
    img: PilImage = qr.make_image(image_factory=PilImage, fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def new_token() -> str:
    return uuid.uuid4().hex


# ---- 用户 / 权限 ----


@app.post("/api/users")
def create_user():
    payload = request.json or {}
    required = ["username", "name", "password", "role"]
    if not all(k in payload for k in required):
        return jsonify({"error": "Missing required fields"}), 400
    with SessionLocal() as session:
        existing = session.scalars(select(User).where(User.username == payload["username"])).first()
        if existing:
            return jsonify({"error": "Username already exists"}), 400
        user = User(
            username=payload["username"],
            name=payload["name"],
            password_hash=generate_password_hash(payload["password"]),
            role=payload.get("role", "worker"),
            permissions=payload.get("permissions"),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return jsonify(user_to_dict(user))


@app.post("/api/login")
def login():
    payload = request.json or {}
    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        return jsonify({"error": "Missing credentials"}), 400
    with SessionLocal() as session:
        user = session.scalars(select(User).where(User.username == username, User.is_active == True)).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Invalid username or password"}), 401
        return jsonify(user_to_dict(user))


@app.get("/api/users")
def list_users():
    with SessionLocal() as session:
        users = session.scalars(select(User)).all()
        return jsonify([user_to_dict(u) for u in users])


# ---- 人员管理 ----


@app.post("/api/personnel")
def create_personnel():
    payload = request.json or {}
    required = ["name", "employee_id", "role"]
    if not all(payload.get(k) for k in required):
        return jsonify({"error": "Missing required fields: name, employee_id, role"}), 400

    with SessionLocal() as session:
        existing_emp = session.scalars(select(Personnel).where(Personnel.employee_id == payload["employee_id"])).first()
        if existing_emp:
            return jsonify({"error": "Employee ID already exists"}), 400

        qr_token = payload.get("qr_token") or new_token()
        existing_token = session.scalars(select(Personnel).where(Personnel.qr_token == qr_token)).first()
        if existing_token:
            return jsonify({"error": "QR token already exists"}), 400

        person = Personnel(
            name=payload["name"],
            employee_id=payload["employee_id"],
            role=payload["role"],
            allowed_operations=payload.get("allowed_operations"),
            qr_token=qr_token,
        )
        session.add(person)
        session.commit()
        session.refresh(person)
        qr_image = generate_qr_base64(person.qr_token)
        return jsonify({"personnel": personnel_to_dict(person), "qr_image_base64": qr_image})


@app.get("/api/personnel")
def list_personnel():
    with SessionLocal() as session:
        people = session.scalars(select(Personnel).order_by(Personnel.created_at.desc())).all()
        return jsonify([personnel_to_dict(p) for p in people])


def material_to_dict(m: Material):
    return {
        "id": m.id,
        "name": m.name,
        "batch_code": m.batch_code,
        "supplier": m.supplier,
        "inspection_result": m.inspection_result,
        "stock_qty": m.stock_qty,
        "qr_token": m.qr_token,
        "extra": m.extra,
        "created_at": m.created_at.isoformat(),
    }


def personnel_to_dict(p: Personnel):
    return {
        "id": p.id,
        "name": p.name,
        "employee_id": p.employee_id,
        "role": p.role,
        "allowed_operations": p.allowed_operations,
        "qr_token": p.qr_token,
        "created_at": p.created_at.isoformat(),
    }


def product_to_dict(p: Product):
    return {
        "id": p.id,
        "name": p.name,
        "status": p.status,
        "final_inspection": p.final_inspection,
        "linked_materials": p.linked_materials,
        "process_data": p.process_data,
        "qr_token": p.qr_token,
        "created_at": p.created_at.isoformat(),
    }


def process_to_dict(p: Process):
    return {
        "id": p.id,
        "name": p.name,
        "sequence": p.sequence,
        "description": p.description,
        "created_at": p.created_at.isoformat(),
    }


# ---- 基础数据：工序 ----


@app.post("/api/processes")
def create_process():
    payload = request.json or {}
    if not payload.get("name"):
        return jsonify({"error": "Missing name"}), 400
    with SessionLocal() as session:
        process = Process(
            name=payload["name"],
            sequence=payload.get("sequence"),
            description=payload.get("description"),
        )
        session.add(process)
        session.commit()
        session.refresh(process)
        return jsonify(process_to_dict(process))


@app.get("/api/processes")
def list_processes():
    with SessionLocal() as session:
        items = session.scalars(select(Process).order_by(Process.sequence)).all()
        return jsonify([process_to_dict(p) for p in items])


def user_to_dict(u: User):
    return {
        "id": u.id,
        "username": u.username,
        "name": u.name,
        "role": u.role,
        "permissions": u.permissions,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat(),
    }


def work_order_to_dict(w: WorkOrder):
    return {
        "id": w.id,
        "code": w.code,
        "product_name": w.product_name,
        "material_batch": w.material_batch,
        "plan_qty": w.plan_qty,
        "line": w.line,
        "status": w.status,
        "planned_start": w.planned_start,
        "planned_end": w.planned_end,
        "qr_token": w.qr_token,
        "completion_qr_token": w.completion_qr_token,
        "created_by": w.created_by,
        "notes": w.notes,
        "created_at": w.created_at.isoformat(),
    }


    def require_personnel(session, role: str, employee_id: str):
        """Ensure a personnel with given role and employee_id exists; return tuple(person, error_response)."""
        if not employee_id:
            return None, (jsonify({"error": "employee_id is required"}), 400)
        person = session.scalars(select(Personnel).where(Personnel.employee_id == employee_id, Personnel.role == role)).first()
        if not person:
            return None, (jsonify({"error": f"Personnel not found for role {role} and employee_id {employee_id}"}), 403)
        return person, None


def progress_to_dict(p: WorkOrderProgress):
    return {
        "id": p.id,
        "work_order_id": p.work_order_id,
        "actual_qty": p.actual_qty,
        "defect_qty": p.defect_qty,
        "operator_id": p.operator_id,
        "note": p.note,
        "created_at": p.created_at.isoformat(),
    }


def exception_to_dict(e: WorkOrderException):
    return {
        "id": e.id,
        "work_order_id": e.work_order_id,
        "exception_type": e.exception_type,
        "description": e.description,
        "action": e.action,
        "status": e.status,
        "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
        "created_at": e.created_at.isoformat(),
    }


def inspection_to_dict(r: InspectionRecord):
    return {
        "id": r.id,
        "object_type": r.object_type,
        "object_token": r.object_token,
        "result": r.result,
        "inspector": r.inspector,
        "items": r.items,
        "note": r.note,
        "created_at": r.created_at.isoformat(),
    }


def receipt_to_dict(r: MaterialReceipt):
    return {
        "id": r.id,
        "material_id": r.material_id,
        "location": r.location,
        "qty": r.qty,
        "operator": r.operator,
        "created_at": r.created_at.isoformat(),
    }


def product_move_to_dict(m: ProductInventoryMove):
    return {
        "id": m.id,
        "product_id": m.product_id,
        "product_name": m.product_name,
        "direction": m.direction,
        "qty": m.qty,
        "location": m.location,
        "order_code": m.order_code,
        "customer": m.customer,
        "note": m.note,
        "created_at": m.created_at.isoformat(),
    }


@app.post("/api/materials")
def create_material():
    payload = request.json or {}
    required = ["name", "batch_code", "supplier", "inspection_result", "stock_qty"]
    if not all(k in payload for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    with SessionLocal() as session:
        token = new_token()
        material = Material(
            name=payload["name"],
            batch_code=payload["batch_code"],
            supplier=payload["supplier"],
            inspection_result=payload["inspection_result"],
            stock_qty=int(payload.get("stock_qty", 0)),
            qr_token=token,
            extra=payload.get("extra"),
        )
        session.add(material)
        session.commit()
        session.refresh(material)
        qr_image = generate_qr_base64(token)
        return jsonify({"material": material_to_dict(material), "qr_image_base64": qr_image})


@app.get("/api/materials")
def list_materials():
    with SessionLocal() as session:
        items = session.scalars(select(Material)).all()
        return jsonify([material_to_dict(m) for m in items])


@app.get("/api/materials/<int:material_id>")
def get_material(material_id: int):
    with SessionLocal() as session:
        material = session.get(Material, material_id)
        if not material:
            return jsonify({"error": "Material not found"}), 404
        return jsonify(material_to_dict(material))



@app.post("/api/products")
def create_product():
    payload = request.json or {}
    required = ["name", "status"]
    if not all(k in payload for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    with SessionLocal() as session:
        token = new_token()
        product = Product(
            name=payload["name"],
            status=payload.get("status", "WIP"),
            final_inspection=payload.get("final_inspection"),
            linked_materials=payload.get("linked_materials"),
            process_data=payload.get("process_data"),
            qr_token=token,
        )
        session.add(product)
        session.commit()
        session.refresh(product)
        qr_image = generate_qr_base64(token)
        return jsonify({"product": product_to_dict(product), "qr_image_base64": qr_image})


# ---- 生产工单 ----


@app.post("/api/workorders")
def create_work_order():
    payload = request.json or {}
    required = ["product_name", "plan_qty"]
    if not all(k in payload for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    with SessionLocal() as session:
        # only manager with matching employee_id can create work order
        _, err = require_personnel(session, "manager", payload.get("employee_id"))
        if err:
            return err

        code = payload.get("code") or f"WO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        token = new_token()
        wo = WorkOrder(
            code=code,
            product_name=payload["product_name"],
            material_batch=payload.get("material_batch"),
            plan_qty=int(payload.get("plan_qty", 0)),
            line=payload.get("line"),
            status=payload.get("status", "待执行"),
            planned_start=payload.get("planned_start"),
            planned_end=payload.get("planned_end"),
            qr_token=token,
            created_by=payload.get("created_by"),
            notes=payload.get("notes"),
        )
        session.add(wo)
        session.commit()
        session.refresh(wo)
        qr_image = generate_qr_base64(token)
        return jsonify({"work_order": work_order_to_dict(wo), "qr_image_base64": qr_image})


@app.get("/api/workorders")
def list_work_orders():
    with SessionLocal() as session:
        orders = session.scalars(select(WorkOrder).order_by(WorkOrder.created_at.desc())).all()
        result = []
        for w in orders:
            totals = session.execute(
                select(func.coalesce(func.sum(WorkOrderProgress.actual_qty), 0), func.coalesce(func.sum(WorkOrderProgress.defect_qty), 0)).where(
                    WorkOrderProgress.work_order_id == w.id
                )
            ).first()
            actual_sum, defect_sum = totals if totals else (0, 0)
            data = work_order_to_dict(w)
            data.update({"actual_qty": int(actual_sum or 0), "defect_qty": int(defect_sum or 0)})
            result.append(data)
        return jsonify(result)


@app.post("/api/workorders/<int:work_order_id>/progress")
def add_work_order_progress(work_order_id: int):
    payload = request.json or {}
    with SessionLocal() as session:
        wo = session.get(WorkOrder, work_order_id)
        if not wo:
            return jsonify({"error": "Work order not found"}), 404

        operator_qr = payload.get("operator_qr_token")
        operator_emp_id = payload.get("employee_id")
        operator = None

        # 优先用二维码，否则用工号；必须是 operator 角色
        if operator_qr:
            operator = session.scalars(select(Personnel).where(Personnel.qr_token == operator_qr, Personnel.role == "operator")).first()
            if not operator:
                return jsonify({"error": "Operator not found for qr token"}), 404
        else:
            operator, err = require_personnel(session, "operator", operator_emp_id)
            if err:
                return err

        operator_id = operator.id if operator else None

        prog = WorkOrderProgress(
            work_order_id=work_order_id,
            actual_qty=int(payload.get("actual_qty", 0)),
            defect_qty=int(payload.get("defect_qty", 0)),
            operator_id=operator_id,
            note=payload.get("note"),
        )
        session.add(prog)
        session.flush()  # ensure progress row is available for aggregation

        # 计算累计实绩以判断完工
        total_actual = session.execute(
            select(func.coalesce(func.sum(WorkOrderProgress.actual_qty), 0)).where(WorkOrderProgress.work_order_id == work_order_id)
        ).scalar_one()

        if wo.status == "待执行":
            wo.status = "执行中"
        if wo.plan_qty and int(total_actual or 0) >= wo.plan_qty:
            wo.status = "完成"
            if not wo.completion_qr_token:
                wo.completion_qr_token = new_token()

        session.commit()
        session.refresh(prog)
        session.refresh(wo)
        return jsonify({"progress": progress_to_dict(prog), "work_order": work_order_to_dict(wo)})


@app.get("/api/workorders/<int:work_order_id>/progress")
def list_work_order_progress(work_order_id: int):
    with SessionLocal() as session:
        items = session.scalars(select(WorkOrderProgress).where(WorkOrderProgress.work_order_id == work_order_id).order_by(WorkOrderProgress.created_at)).all()
        return jsonify([progress_to_dict(p) for p in items])


@app.post("/api/workorders/<int:work_order_id>/exceptions")
def create_work_order_exception(work_order_id: int):
    payload = request.json or {}
    if not payload.get("exception_type"):
        return jsonify({"error": "Missing exception_type"}), 400
    with SessionLocal() as session:
        _, err = require_personnel(session, "manager", payload.get("employee_id"))
        if err:
            return err
        wo = session.get(WorkOrder, work_order_id)
        if not wo:
            return jsonify({"error": "Work order not found"}), 404
        exc = WorkOrderException(
            work_order_id=work_order_id,
            exception_type=payload["exception_type"],
            description=payload.get("description"),
            action=payload.get("action"),
            status=payload.get("status", "open"),
        )
        session.add(exc)
        session.commit()
        session.refresh(exc)
        return jsonify(exception_to_dict(exc))


@app.post("/api/workorders/<int:work_order_id>/exceptions/<int:exc_id>/resolve")
def resolve_work_order_exception(work_order_id: int, exc_id: int):
    payload = request.json or {}
    with SessionLocal() as session:
        _, err = require_personnel(session, "manager", payload.get("employee_id"))
        if err:
            return err
        exc = session.get(WorkOrderException, exc_id)
        if not exc or exc.work_order_id != work_order_id:
            return jsonify({"error": "Exception not found"}), 404
        exc.status = payload.get("status", "resolved")
        exc.action = payload.get("action", exc.action)
        exc.resolved_at = datetime.utcnow()
        session.commit()
        session.refresh(exc)
        return jsonify(exception_to_dict(exc))


# ---- 质检 / 追溯 ----


@app.post("/api/inspections")
def create_inspection():
    payload = request.json or {}
    object_type = payload.get("object_type")
    result = payload.get("result")
    if not object_type or not result:
        return jsonify({"error": "Missing required fields"}), 400
    if object_type not in {"material", "product"}:
        return jsonify({"error": "object_type must be material or product"}), 400

    with SessionLocal() as session:
        _, err = require_personnel(session, "qa", payload.get("employee_id"))
        if err:
            return err
        if object_type == "material":
            material = None
            qr_image = None

            material_id = payload.get("material_id")
            if material_id:
                material = session.get(Material, material_id)
                if not material:
                    return jsonify({"error": "Material not found"}), 404
            else:
                required_fields = ["name", "batch_code", "supplier"]
                if not all(payload.get(k) for k in required_fields):
                    return jsonify({"error": "Missing material fields: name, batch_code, supplier"}), 400
                token = new_token()
                material = Material(
                    name=payload["name"],
                    batch_code=payload["batch_code"],
                    supplier=payload["supplier"],
                    inspection_result=payload.get("inspection_result", result),
                    stock_qty=int(payload.get("qty", 0)),
                    qr_token=token,
                    extra=payload.get("extra"),
                )
                session.add(material)
                session.flush()

            receipt_obj = None
            if payload.get("qty") is not None:
                qty = int(payload.get("qty", 0))
                material.stock_qty = (material.stock_qty or 0) + qty
                receipt_obj = MaterialReceipt(
                    material_id=material.id,
                    location=payload.get("location"),
                    qty=qty,
                    operator=payload.get("operator"),
                )
                session.add(receipt_obj)

            record = InspectionRecord(
                object_type="material",
                object_token=material.qr_token,
                result=result,
                inspector=payload.get("inspector"),
                items=payload.get("items"),
                note=payload.get("note"),
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            qr_image = generate_qr_base64(material.qr_token)
            response = {
                "inspection": inspection_to_dict(record),
                "material": material_to_dict(material),
                "qr_image_base64": qr_image,
            }
            if receipt_obj:
            _, err = require_personnel(session, "manager", payload.get("employee_id"))
            if err:
                return err
                response["receipt"] = receipt_to_dict(receipt_obj)
            return jsonify(response)

        # product: must scan completion work order QR to obtain product info for inbound
        work_token = payload.get("object_token") or payload.get("work_order_token")
        if not work_token:
            return jsonify({"error": "work order completion QR token is required for product inspection"}), 400
        wo = session.scalars(select(WorkOrder).where(WorkOrder.completion_qr_token == work_token)).first()
        if not wo:
            return jsonify({"error": "Work order not found for provided completion QR token"}), 404

        qty = int(payload.get("qty", 0))
        product = Product(
            name=wo.product_name,
            status=payload.get("status", result),
            final_inspection=result,
            linked_materials=wo.material_batch,
            process_data=wo.code,
            qr_token=new_token(),
        )
        session.add(product)
        session.flush()

        move = ProductInventoryMove(
            product_id=product.id,
            product_name=product.name,
            direction="in",
            qty=qty,
            location=payload.get("location"),
            order_code=wo.code,
            customer=payload.get("customer"),
            note=payload.get("note"),
        )
        session.add(move)

        record = InspectionRecord(
            object_type="product",
            object_token=product.qr_token,
            result=result,
            inspector=payload.get("inspector"),
            items=payload.get("items"),
            note=payload.get("note"),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        session.refresh(move)
        qr_image = generate_qr_base64(product.qr_token)
        return jsonify(
            {
                "inspection": inspection_to_dict(record),
                "inventory_move": product_move_to_dict(move),
                "work_order": work_order_to_dict(wo),
                "product": product_to_dict(product),
                "qr_image_base64": qr_image,
            }
        )


@app.get("/api/inspections")
def list_inspections():
    with SessionLocal() as session:
        items = session.scalars(select(InspectionRecord).order_by(InspectionRecord.created_at.desc())).all()
        return jsonify([inspection_to_dict(i) for i in items])


@app.get("/api/trace/product/<string:qr_token>")
def trace_product(qr_token: str):
    with SessionLocal() as session:
        product = session.scalars(select(Product).where(Product.qr_token == qr_token)).first()
        if not product:
            return jsonify({"error": "Product not found for token"}), 404

        work_order = None
        if product.process_data:
            work_order = session.scalars(select(WorkOrder).where(WorkOrder.code == product.process_data)).first()

        materials = []
        if work_order and work_order.material_batch:
            materials = session.scalars(select(Material).where(Material.batch_code == work_order.material_batch)).all()

        material_inspections = []
        if materials:
            material_tokens = [m.qr_token for m in materials]
            material_inspections = session.scalars(
                select(InspectionRecord)
                .where(InspectionRecord.object_type == "material", InspectionRecord.object_token.in_(material_tokens))
                .order_by(InspectionRecord.created_at.desc())
            ).all()

        product_inspections = session.scalars(
            select(InspectionRecord)
            .where(InspectionRecord.object_type == "product", InspectionRecord.object_token == product.qr_token)
            .order_by(InspectionRecord.created_at.desc())
        ).all()

        operators = []
        if work_order:
            operator_ids = [p.operator_id for p in session.scalars(select(WorkOrderProgress).where(WorkOrderProgress.work_order_id == work_order.id)).all() if p.operator_id]
            if operator_ids:
                operators = session.scalars(select(Personnel).where(Personnel.id.in_(operator_ids))).all()

        return jsonify(
            {
                "product": {
                    "name": product.name,
                    "status": product.status,
                    "final_inspection": product.final_inspection,
                    "created_at": product.created_at.isoformat(),
                },
                "product_inspections": [
                    {
                        "result": i.result,
                        "inspector": i.inspector,
                        "note": i.note,
                        "created_at": i.created_at.isoformat(),
                    }
                    for i in product_inspections
                ],
                "work_order": work_order_to_dict(work_order) if work_order else None,
                "materials": [
                    {
                        "name": m.name,
                        "batch_code": m.batch_code,
                        "supplier": m.supplier,
                        "inspection_result": m.inspection_result,
                    }
                    for m in materials
                ],
                "material_inspections": [
                    {
                        "result": i.result,
                        "inspector": i.inspector,
                        "note": i.note,
                        "created_at": i.created_at.isoformat(),
                    }
                    for i in material_inspections
                ],
                "operators": [
                    {
                        "name": p.name,
                        "employee_id": p.employee_id,
                        "role": p.role,
                    }
                    for p in operators
                ],
            }
        )



@app.get("/api/scan/<string:qr_token>")
def scan_token(qr_token: str):
    with SessionLocal() as session:
        material = session.scalars(select(Material).where(Material.qr_token == qr_token)).first()
        if material:
            return jsonify({"type": "material", "data": material_to_dict(material)})
        person = session.scalars(select(Personnel).where(Personnel.qr_token == qr_token)).first()
        if person:
            return jsonify({"type": "personnel", "data": personnel_to_dict(person)})
        product = session.scalars(select(Product).where(Product.qr_token == qr_token)).first()
        if product:
            return jsonify({"type": "product", "data": product_to_dict(product)})
        work_order = session.scalars(select(WorkOrder).where((WorkOrder.qr_token == qr_token) | (WorkOrder.completion_qr_token == qr_token))).first()
        if work_order:
            typ = "work_order_completion" if work_order.completion_qr_token == qr_token else "work_order"
            return jsonify({"type": typ, "data": work_order_to_dict(work_order)})
    return jsonify({"error": "QR token not found"}), 404


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
