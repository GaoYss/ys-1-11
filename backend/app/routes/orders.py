from datetime import date

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from ..extensions import db
from ..models import PurchaseOrder, PurchaseOrderItem

orders_bp = Blueprint("orders", __name__)


def get_recent_avg_price(ingredient_id, limit=10):
    subquery = (
        PurchaseOrderItem.query.filter_by(ingredient_id=ingredient_id)
        .join(PurchaseOrder)
        .filter(PurchaseOrder.status.in_(["approved", "received"]))
        .order_by(PurchaseOrder.created_at.desc())
        .limit(limit)
        .subquery()
    )
    result = db.session.query(func.avg(subquery.c.unit_price)).scalar()
    return float(result) if result else None


@orders_bp.get("")
def list_orders():
    status = request.args.get("status", "").strip()
    query = PurchaseOrder.query
    if status:
        query = query.filter_by(status=status)
    orders = query.order_by(PurchaseOrder.created_at.desc()).all()
    return jsonify([order.to_dict() for order in orders])


@orders_bp.get("/avg-price/<int:ingredient_id>")
def get_ingredient_avg_price(ingredient_id):
    avg_price = get_recent_avg_price(ingredient_id)
    return jsonify({"ingredientId": ingredient_id, "avgPrice": avg_price})


@orders_bp.post("")
def create_order():
    data = request.get_json() or {}
    expected_date = data.get("expectedDate")
    order = PurchaseOrder(
        order_no=data["orderNo"],
        supplier_id=data["supplierId"],
        status=data.get("status", "draft"),
        expected_date=date.fromisoformat(expected_date) if expected_date else None,
        remark=data.get("remark"),
    )
    for item in data.get("items", []):
        unit_price = float(item["unitPrice"])
        avg_price = item.get("referenceAvgPrice")
        if avg_price is None:
            avg_price = get_recent_avg_price(item["ingredientId"])
        is_overpriced = bool(item.get("isOverpriced", False))
        if avg_price and not is_overpriced:
            is_overpriced = unit_price > avg_price * 1.1
        order.items.append(
            PurchaseOrderItem(
                ingredient_id=item["ingredientId"],
                quantity=float(item["quantity"]),
                unit_price=unit_price,
                reference_avg_price=avg_price,
                is_overpriced=is_overpriced,
            )
        )
    db.session.add(order)
    db.session.commit()
    return order.to_dict(), 201


@orders_bp.put("/<int:order_id>/status")
def update_order_status(order_id):
    order = PurchaseOrder.query.get_or_404(order_id)
    data = request.get_json() or {}
    order.status = data.get("status", order.status)
    db.session.commit()
    return order.to_dict()
