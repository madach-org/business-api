import re

from app import app, db, User, Customer, Product, Sale


app.config["TESTING"] = True
client = app.test_client()


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"[PASS] {message}")


def csrf_token(response):
    match = re.search(
        r'name="csrf_token"\s+value="([^"]+)"',
        response.get_data(as_text=True),
    )
    if not match:
        raise AssertionError("CSRF token missing from form")
    return match.group(1)


def database_snapshot():
    return {
        "users": db.session.query(User.id).count(),
        "customers": db.session.query(Customer.id).count(),
        "products": db.session.query(Product.id).count(),
        "sales": db.session.query(Sale.id).count(),
        "stock": tuple(
            db.session.query(Product.id, Product.quantity)
            .order_by(Product.id)
            .all()
        ),
    }


with app.app_context():
    before = database_snapshot()
    user = User.query.order_by(User.id).first()

    check(user is not None, "An existing test account is available")

    # Public login and registration pages
    login_page = client.get("/login")
    check(login_page.status_code == 200, "Login page loads")

    register_page = client.get("/register")
    check(register_page.status_code == 200, "Registration page loads")

    # Protected web and API routes
    dashboard_response = client.get("/dashboard")
    check(
        dashboard_response.status_code == 302
        and "/login" in dashboard_response.headers.get("Location", ""),
        "Unauthenticated dashboard redirects to login",
    )

    customers_response = client.get("/customers")
    check(
        customers_response.status_code == 401,
        "Unauthenticated customer API returns 401",
    )

    sales_response = client.get("/sales")
    check(
        sales_response.status_code == 401,
        "Unauthenticated sales API returns 401",
    )

    # Missing CSRF token must block state-changing requests
    logout_response = client.post("/logout")
    check(
        logout_response.status_code == 400,
        "Logout without a CSRF token is rejected",
    )

    api_post_response = client.post(
        "/customers",
        json={"name": "Security Test"},
    )
    check(
        api_post_response.status_code == 400,
        "Customer API POST without a CSRF token is rejected",
    )

    api_error = api_post_response.get_json()
    check(
        isinstance(api_error, dict)
        and api_error.get("error") == "CSRF validation failed",
        "API CSRF failure returns a JSON error",
    )

    # Invalid registration: valid CSRF token, but too-short password.
    registration_token = csrf_token(register_page)
    invalid_registration = client.post(
        "/register",
        data={
            "csrf_token": registration_token,
            "email": "day49-invalid-password@example.invalid",
            "password": "short",
        },
    )
    check(
        invalid_registration.status_code == 200,
        "Short registration password is rejected without redirect",
    )
    check(
        b"at least 8 characters"
        in invalid_registration.data.lower(),
        "Registration displays the password-length error",
    )

    # Invalid login: use an existing account, but a deliberately wrong password.
    login_token = csrf_token(login_page)
    invalid_login = client.post(
        "/login",
        data={
            "csrf_token": login_token,
            "email": user.email,
            "password": "definitely-wrong-password",
        },
    )
    check(
        invalid_login.status_code == 200,
        "Invalid login credentials are rejected",
    )
    check(
        b"invalid email or password"
        in invalid_login.data.lower(),
        "Login displays a generic authentication error",
    )

    after = database_snapshot()
    check(
        before == after,
        "All database counts and product stock remain unchanged",
    )

print("[PASS] Day 49 security tests completed")
