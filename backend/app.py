import base64
import io
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import select

import config
from db import Base, engine, SessionLocal
from models import Material, Personnel, Product

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


@app.post("/api/personnel")
def create_personnel():
    payload = request.json or {}
    required = ["name", "employee_id", "role"]
    if not all(k in payload for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    with SessionLocal() as session:
        token = new_token()
        person = Personnel(
            name=payload["name"],
            employee_id=payload["employee_id"],
            role=payload["role"],
            allowed_operations=payload.get("allowed_operations"),
            qr_token=token,
        )
        session.add(person)
        session.commit()
        session.refresh(person)
        qr_image = generate_qr_base64(token)
        return jsonify({"personnel": personnel_to_dict(person), "qr_image_base64": qr_image})


@app.get("/api/personnel")
def list_personnel():
    with SessionLocal() as session:
        items = session.scalars(select(Personnel)).all()
        return jsonify([personnel_to_dict(p) for p in items])


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


@app.get("/api/products")
def list_products():
    with SessionLocal() as session:
        items = session.scalars(select(Product)).all()
        return jsonify([product_to_dict(p) for p in items])


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
    return jsonify({"error": "QR token not found"}), 404


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
