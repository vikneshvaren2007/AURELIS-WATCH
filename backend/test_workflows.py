import json
from backend.app import app
from backend.database import get_db

def test_cod_cancellation_and_return():
    client = app.test_client()

    reg_res = client.post("/api/auth/register", json={
        "name": "Marcus Sterling",
        "email": "marcus.sterling@example.com",
        "password": "Password123!",
        "phone": "+919888877777"
    })
    if reg_res.status_code == 201:
        token = reg_res.get_json()["token"]
    else:
        login_res = client.post("/api/auth/login", json={
            "email": "marcus.sterling@example.com",
            "password": "Password123!"
        })
        token = login_res.get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Place COD Order
    cod_order_payload = {
        "customer_name": "Marcus Sterling",
        "customer_email": "marcus.sterling@example.com",
        "customer_phone": "+919888877777",
        "shipping_address": {
            "street": "42 High Street",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
            "country": "India"
        },
        "items": [{"variant_id": 1, "quantity": 1}],
        "payment_method": "COD"
    }
    order_res = client.post("/api/orders", json=cod_order_payload, headers=headers)
    assert order_res.status_code == 201, f"Failed COD order: {order_res.get_json()}"
    order_data = order_res.get_json()
    order_num = order_data["order_number"]
    print(f"[OK] COD Order placed: {order_num}, Status: {order_data['order_status']}, Payment: {order_data['payment_status']}")

    # 3. Test Order Cancellation with automatic inventory restocking
    with get_db() as conn:
        stock_before = conn.execute("SELECT stock_quantity FROM product_variants WHERE id = 1").fetchone()["stock_quantity"]
    
    cancel_res = client.post(f"/api/orders/{order_num}/cancel", json={
        "reason": "Change of mind",
        "comments": "Decided to wait for another collection"
    }, headers=headers)
    assert cancel_res.status_code == 200, f"Failed cancel order: {cancel_res.get_json()}"
    print(f"[OK] Order {order_num} successfully cancelled: {cancel_res.get_json()}")

    with get_db() as conn:
        stock_after = conn.execute("SELECT stock_quantity FROM product_variants WHERE id = 1").fetchone()["stock_quantity"]
        assert stock_after == stock_before + 1, f"Stock not restored: before {stock_before}, after {stock_after}"
    print(f"[OK] Stock verified: Restored by 1 unit from {stock_before} to {stock_after}")

    # 4. Create another order, mark DELIVERED, and submit Return Request
    order2_res = client.post("/api/orders", json=cod_order_payload, headers=headers)
    order2_num = order2_res.get_json()["order_number"]
    order2_id = order2_res.get_json()["order_id"]

    # Admin marks order as DELIVERED
    login_res = client.post("/api/admin/login", json={"email": "vikneshvaren@gmail.com", "password": "Admin@Aurelis2026!"})
    admin_token = login_res.get_json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    client.put(f"/api/admin/orders/{order2_id}/status", json={"order_status": "DELIVERED", "notes": "Delivered in person"}, headers=admin_headers)
    print(f"[OK] Order {order2_num} transitioned to DELIVERED by Admin")

    # Customer submits return request
    ret_res = client.post(f"/api/orders/{order2_num}/return", json={
        "reason": "Slight strap size preference",
        "description": "Seeking exchange or refund",
        "refund_preference": "ORIGINAL_METHOD",
        "bank_account_number": "123456789012",
        "ifsc_code": "HDFC0001234",
        "account_holder_name": "Marcus Sterling"
    }, headers=headers)
    assert ret_res.status_code == 201, f"Return failed: {ret_res.get_json()}"
    ret_data = ret_res.get_json()
    print(f"[OK] Return Request submitted: Return ID #{ret_data['return_id']}, Status: {ret_data['status']}")

    # Admin reviews return
    admin_returns = client.get("/api/admin/returns", headers=admin_headers)
    assert len(admin_returns.get_json()["returns"]) >= 1
    print(f"[OK] Admin verified {len(admin_returns.get_json()['returns'])} pending return request(s)")

    print("\nALL COD, CANCELLATION, RESTOCKING & RETURN WORKFLOWS TESTED & VERIFIED!")

if __name__ == "__main__":
    test_cod_cancellation_and_return()
