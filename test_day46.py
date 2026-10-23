from app import app, db, User, Sale, Product

app.config["TESTING"] = True


def login_as(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


with app.app_context():
    users = User.query.order_by(User.id).limit(2).all()

    if len(users) < 2:
        raise SystemExit("[STOP] Expected two existing users.")

    user_ids = [user.id for user in users]

    before = {
        "users": User.query.count(),
        "sales": Sale.query.count(),
        "products": Product.query.count(),
        "stock": [
            (p.id, p.quantity)
            for p in Product.query.order_by(Product.id).all()
        ],
    }

# Unauthenticated requests must be blocked.
client = app.test_client()

response = client.get("/reports/sales-summary")
assert response.status_code == 401, (
    f"Unauthenticated summary returned {response.status_code}"
)
print("[PASS] Unauthenticated summary access blocked")

response = client.get("/reports/sales-export.csv")
assert response.status_code == 401, (
    f"Unauthenticated CSV returned {response.status_code}"
)
print("[PASS] Unauthenticated CSV access blocked")

# Test reports separately for each existing user.
for user_id in user_ids:
    client = app.test_client()
    login_as(client, user_id)

    response = client.get("/reports/sales-summary")
    assert response.status_code == 200, response.get_data(as_text=True)
    summary = response.get_json()

    with app.app_context():
        own_count = Sale.query.filter_by(user_id=user_id).count()

    assert summary["total_sales"] == own_count, (
        f"User {user_id}: sales count does not match owned sales"
    )
    assert "estimated_sales_value" in summary
    assert "top_products" in summary
    print(f"[PASS] User {user_id}: summary matches owned sales")

    # A valid date range should be accepted.
    response = client.get(
        "/reports/sales-summary"
        "?start_date=2000-01-01&end_date=2099-12-31"
    )
    assert response.status_code == 200, response.get_data(as_text=True)

    filtered = response.get_json()
    assert filtered["total_sales"] == own_count
    print(f"[PASS] User {user_id}: valid date range accepted")

    # Invalid dates and reversed date ranges should be rejected.
    for query in (
        "?start_date=not-a-date",
        "?start_date=2026-10-22&end_date=2026-10-01",
    ):
        response = client.get("/reports/sales-summary" + query)
        assert response.status_code == 400, (
            f"Expected HTTP 400 for {query}, "
            f"received {response.status_code}: "
            f"{response.get_data(as_text=True)}"
        )

    print(f"[PASS] User {user_id}: invalid date ranges rejected")

    # Check CSV download response and required columns.
    response = client.get(
        "/reports/sales-export.csv"
        "?start_date=2000-01-01&end_date=2099-12-31"
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    assert "text/csv" in response.content_type
    assert "attachment;" in response.headers.get(
        "Content-Disposition", ""
    )

    csv_text = response.get_data(as_text=True)
    assert "Sale ID" in csv_text
    assert "Estimated Line Value" in csv_text
    print(f"[PASS] User {user_id}: CSV download and columns")

# Verify that the tests did not alter existing records or stock.
with app.app_context():
    after = {
        "users": User.query.count(),
        "sales": Sale.query.count(),
        "products": Product.query.count(),
        "stock": [
            (p.id, p.quantity)
            for p in Product.query.order_by(Product.id).all()
        ],
    }

assert before == after, (
    f"Database counts or stock changed: before={before}, after={after}"
)

print("[PASS] Database records and product stock unchanged")
print("[PASS] Day 46 tests completed")
