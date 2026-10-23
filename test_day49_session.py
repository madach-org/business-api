import re

from app import app, db, User, Customer, Product, Sale

app.config["TESTING"] = True
client = app.test_client()


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"[PASS] {message}")


def snapshot():
    return (
        User.query.count(),
        Customer.query.count(),
        Product.query.count(),
        Sale.query.count(),
        tuple(
            db.session.query(Product.id, Product.quantity)
            .order_by(Product.id)
            .all()
        ),
    )


with app.app_context():
    before = snapshot()
    user = User.query.order_by(User.id).first()
    check(user is not None, "Existing user available for session test")
    check(user.is_active, "Test user account is active")

    # Establish a test login session.
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True

    # Load the dashboard within that same session.
    dashboard = client.get("/dashboard")
    check(
        dashboard.status_code == 200,
        "Authenticated user can access the dashboard",
    )

    # Extract the CSRF token from the dashboard's logout form.
    html = dashboard.get_data(as_text=True)
    match = re.search(
        r'name="csrf_token"\s+value="([^"]+)"',
        html,
    )
    check(match is not None, "Dashboard logout form has a CSRF token")
    token = match.group(1)

    # Submit logout using the token from this session.
    logout_response = client.post(
        "/logout",
        data={"csrf_token": token},
    )
    check(
        logout_response.status_code == 302
        and "/login" in logout_response.headers.get("Location", ""),
        "Logout with a valid CSRF token succeeds",
    )

    # Confirm the session no longer grants dashboard access.
    after_logout = client.get("/dashboard")
    check(
        after_logout.status_code == 302
        and "/login" in after_logout.headers.get("Location", ""),
        "Dashboard access is blocked after logout",
    )

    check(
        before == snapshot(),
        "All database records and stock remain unchanged",
    )

print("[PASS] Day 49 session and logout tests completed")
