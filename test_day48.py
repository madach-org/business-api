from datetime import date, datetime, time, timedelta

from app import (
    app,
    db,
    User,
    Sale,
    Product,
    Customer,
    parse_report_dates,
    sale_date_filters,
    spreadsheet_safe_text,
)

app.config["TESTING"] = True


def login_as(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print("[PASS]", message)


with app.app_context():
    user_ids = [
        user.id
        for user in User.query.order_by(User.id).limit(2).all()
    ]
    check(len(user_ids) == 2, "Two existing users available")

    before = {
        "users": User.query.count(),
        "customers": Customer.query.count(),
        "products": Product.query.count(),
        "sales": Sale.query.count(),
        "stock": [
            (p.id, p.quantity)
            for p in Product.query.order_by(Product.id).all()
        ],
        "sale_dates": [
            (s.id, s.sale_date)
            for s in Sale.query.order_by(Sale.id).all()
        ],
    }

    # Date parser tests use Flask's request context.
    with app.test_request_context(
        "/reports/sales-summary?start_date=2026-10-06&end_date=2026-10-06"
    ):
        start, end, error = parse_report_dates()
        check(
            start == date(2026, 10, 6)
            and end == date(2026, 10, 6)
            and error is None,
            "Same-day date range accepted",
        )

    with app.test_request_context(
        "/reports/sales-summary?start_date=2026-02-30"
    ):
        start, end, error = parse_report_dates()
        check(error is not None, "Impossible calendar date rejected")

    with app.test_request_context(
        "/reports/sales-summary?start_date=2026-1-06"
    ):
        start, end, error = parse_report_dates()
        check(error is not None, "Non-padded date format rejected")

    # Date filters must include all times on the selected end date.
    filters = sale_date_filters(
        date(2026, 10, 6),
        date(2026, 10, 6),
    )
    matching_sales = Sale.query.filter(*filters).all()
    check(
        len(matching_sales) == 2,
        "Both existing sales on the selected end date are included",
    )

    # The maximum date should not overflow when adding one day.
    max_filters = sale_date_filters(end_date=date.max)
    check(
        len(max_filters) == 1,
        "Maximum calendar date filter builds safely",
    )

    # CSV spreadsheet-formula protection.
    for dangerous in ("=1+1", "+1+1", "-1+1", "@SUM(A1)", "\tvalue", "\rvalue"):
        safe = spreadsheet_safe_text(dangerous)
        check(
            safe.startswith("'"),
            f"CSV formula prefix neutralized: {dangerous!r}",
        )

    check(
        spreadsheet_safe_text("Normal customer") == "Normal customer",
        "Ordinary CSV text remains unchanged",
    )

# Verify protected report routes and per-user isolation.
for user_id in user_ids:
    client = app.test_client()
    login_as(client, user_id)

    response = client.get(
        "/reports/sales-summary"
        "?start_date=2026-10-06&end_date=2026-10-06"
    )
    check(
        response.status_code == 200,
        f"User {user_id}: date-filtered summary accessible",
    )

    with app.app_context():
        own_count = Sale.query.filter_by(user_id=user_id).filter(
            *sale_date_filters(
                date(2026, 10, 6),
                date(2026, 10, 6),
            )
        ).count()

    check(
        response.get_json()["total_sales"] == own_count,
        f"User {user_id}: summary contains only owned sales",
    )

    response = client.get(
        "/reports/sales-export.csv"
        "?start_date=2026-10-06&end_date=2026-10-06"
    )
    check(
        response.status_code == 200,
        f"User {user_id}: filtered CSV export succeeds",
    )

# Confirm that tests did not modify existing business data.
with app.app_context():
    after = {
        "users": User.query.count(),
        "customers": Customer.query.count(),
        "products": Product.query.count(),
        "sales": Sale.query.count(),
        "stock": [
            (p.id, p.quantity)
            for p in Product.query.order_by(Product.id).all()
        ],
        "sale_dates": [
            (s.id, s.sale_date)
            for s in Sale.query.order_by(Sale.id).all()
        ],
    }

check(before == after, "All database records and stock remain unchanged")
print("[PASS] Day 48 focused tests completed")
