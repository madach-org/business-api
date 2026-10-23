
import os
import csv
import io
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    redirect,
    url_for,
    flash,
    Response,
)
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


# --------------------------------------------------
# 1. Application configuration
# --------------------------------------------------

load_dotenv()

app = Flask(__name__)

# Session-cookie security settings.
# SECURE=False is for local HTTP development only.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = (
    os.getenv("SESSION_COOKIE_SECURE", "false").strip().lower()
    in {"1", "true", "yes", "on"}
)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "FLASK_SECRET_KEY is missing. "
        "Add it to your .env file."
    )

database_url = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://u0_a262@localhost/business_db",
)

# Support PostgreSQL URLs from hosting providers.
if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://", "postgresql+psycopg2://", 1
    )
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://", "postgresql+psycopg2://", 1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

csrf = CSRFProtect(app)


# --------------------------------------------------
# 2. Authentication and error handling
# --------------------------------------------------

def is_api_request():
    return request.path.startswith((
        "/customers",
        "/products",
        "/sales",
        "/reports",
    ))


@login_manager.unauthorized_handler
def handle_unauthorized():
    if is_api_request():
        return jsonify({
            "error": "Authentication required"
        }), 401

    return redirect(url_for("login"))


@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    if is_api_request():
        return jsonify({
            "error": "CSRF validation failed"
        }), 400

    return error.description, 400


@app.errorhandler(404)
def handle_not_found(error):
    if is_api_request():
        return jsonify({"error": "Resource not found"}), 404

    return "Page not found", 404


# --------------------------------------------------
# 3. Database models
# --------------------------------------------------

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash = db.Column(
        db.String(256),
        nullable=False,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password,
        )


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))

    # Preserves your existing global uniqueness constraint.
    email = db.Column(db.String(100), unique=True)

    notes = db.Column(db.Text)

    sales = db.relationship(
        "Sale",
        back_populates="customer",
    )


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    name = db.Column(db.String(100), nullable=False)

    price = db.Column(
        db.Numeric(12, 2),
        nullable=False,
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    sales = db.relationship(
        "Sale",
        back_populates="product",
    )

    sale_items = db.relationship(
        "SaleItem",
        back_populates="product",
    )


class Sale(db.Model):
    __tablename__ = "sales"

    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customers.id"),
        nullable=False,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False,
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
    )

    sale_date = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp(),
    )

    customer = db.relationship(
        "Customer",
        back_populates="sales",
    )

    product = db.relationship(
        "Product",
        back_populates="sales",
    )

    items = db.relationship(
        "SaleItem",
        back_populates="sale",
    )


class SaleItem(db.Model):
    __tablename__ = "sale_items"

    id = db.Column(db.Integer, primary_key=True)

    sale_id = db.Column(
        db.Integer,
        db.ForeignKey("sales.id"),
        nullable=False,
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False,
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
    )

    sale = db.relationship(
        "Sale",
        back_populates="items",
    )

    product = db.relationship(
        "Product",
        back_populates="sale_items",
    )


# --------------------------------------------------
# 4. Login session loading
# --------------------------------------------------

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


# --------------------------------------------------
# 5. Ownership helpers
# --------------------------------------------------

def get_owned_customer(customer_id):
    return Customer.query.filter_by(
        id=customer_id,
        user_id=current_user.id,
    ).first()


def get_owned_product(product_id):
    return Product.query.filter_by(
        id=product_id,
        user_id=current_user.id,
    ).first()


def get_owned_sale(sale_id):
    return Sale.query.filter_by(
        id=sale_id,
        user_id=current_user.id,
    ).first()


# --------------------------------------------------
# 6. Home
# --------------------------------------------------

@app.route("/")
def home():
    return {"message": "Business API is running"}


# --------------------------------------------------
# 7. Customer API
# --------------------------------------------------

@app.route("/customers", methods=["GET"])
@login_required
def get_customers():
    customers = Customer.query.filter_by(
        user_id=current_user.id,
    ).all()

    return [
        {
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email,
            "notes": customer.notes,
        }
        for customer in customers
    ]


@app.route("/customers/<int:customer_id>", methods=["GET"])
@login_required
def get_customer(customer_id):
    customer = get_owned_customer(customer_id)

    if customer is None:
        return {"error": "Customer not found"}, 404

    return {
        "id": customer.id,
        "name": customer.name,
        "phone": customer.phone,
        "email": customer.email,
        "notes": customer.notes,
    }


@app.route("/customers", methods=["POST"])
@login_required
def create_customerr():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {"error": "A JSON object is required"}, 400

    name = data.get("name")

    if not isinstance(name, str):
        return {"error": "Name is required"}, 400

    name = name.strip()
    phone = data.get("phone")
    email = data.get("email")
    notes = data.get("notes")

    if not 2 <= len(name) <= 100:
        return {
            "error": "Name must be between 2 and 100 characters"
        }, 400

    if phone is not None and not isinstance(phone, str):
        return {"error": "Phone must be text"}, 400

    if email is not None and not isinstance(email, str):
        return {"error": "Email must be text"}, 400

    if notes is not None and not isinstance(notes, str):
        return {"error": "Notes must be text"}, 400

    phone = phone.strip() if phone else None
    email = email.strip().lower() if email else None
    notes = notes.strip() if notes else None

    if phone and len(phone) > 20:
        return {"error": "Phone must not exceed 20 characters"}, 400

    if email and len(email) > 100:
        return {"error": "Email must not exceed 100 characters"}, 400

    if email and (
        "@" not in email
        or "." not in email.rsplit("@", 1)[-1]
    ):
        return {"error": "Invalid email address"}, 400

    try:
        customer = Customer(
            user_id=current_user.id,
            name=name,
            phone=phone,
            email=email,
            notes=notes,
        )

        db.session.add(customer)
        db.session.commit()

        return {
            "message": "Customer created",
            "id": customer.id,
        }, 201

    except IntegrityError:
        db.session.rollback()
        return {
            "error": "A customer with that email may already exist"
        }, 409

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Could not create customer")
        return {"error": "Database operation failed"}, 500


@app.route("/customers/<int:customer_id>", methods=["PUT"])
@login_required
def update_customer(customer_id):
    customer = get_owned_customer(customer_id)

    if customer is None:
        return {"error": "Customer not found"}, 404

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {"error": "A JSON object is required"}, 400

    if "name" in data:
        if not isinstance(data["name"], str):
            return {"error": "Name must be text"}, 400

        name = data["name"].strip()

        if not 2 <= len(name) <= 100:
            return {
                "error": "Name must be between 2 and 100 characters"
            }, 400

        customer.name = name

    if "phone" in data:
        phone = data["phone"]

        if phone is not None and not isinstance(phone, str):
            return {"error": "Phone must be text"}, 400

        phone = phone.strip() if phone else None

        if phone and len(phone) > 20:
            return {"error": "Phone must not exceed 20 characters"}, 400

        customer.phone = phone

    if "email" in data:
        email = data["email"]

        if email is not None and not isinstance(email, str):
            return {"error": "Email must be text"}, 400

        email = email.strip().lower() if email else None

        if email and len(email) > 100:
            return {"error": "Email must not exceed 100 characters"}, 400

        if email and (
            "@" not in email
            or "." not in email.rsplit("@", 1)[-1]
        ):
            return {"error": "Invalid email address"}, 400

        customer.email = email

    if "notes" in data:
        notes = data["notes"]

        if notes is not None and not isinstance(notes, str):
            return {"error": "Notes must be text"}, 400

        customer.notes = notes.strip() if notes else None

    try:
        db.session.commit()
        return {"message": "Customer updated"}

    except IntegrityError:
        db.session.rollback()
        return {
            "error": "A customer with that email may already exist"
        }, 409

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Could not update customer")
        return {"error": "Database operation failed"}, 500


@app.route("/customers/<int:customer_id>", methods=["DELETE"])
@login_required
def delete_customerr(customer_id):
    customer = get_owned_customer(customer_id)

    if customer is None:
        return {"error": "Customer not found"}, 404

    try:
        db.session.delete(customer)
        db.session.commit()
        return {"message": "Customer deleted"}

    except IntegrityError:
        db.session.rollback()
        return {
            "error": "Customer cannot be deleted while related sales exist"
        }, 409

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Could not delete customer")
        return {"error": "Database operation failed"}, 500


# --------------------------------------------------
# 8. Product API
# --------------------------------------------------

@app.route("/products", methods=["GET"])
@login_required
def get_products():
    products = Product.query.filter_by(
        user_id=current_user.id,
    ).order_by(Product.id).all()

    return [
        {
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "quantity": product.quantity,
        }
        for product in products
    ]


@app.route("/products/search")
@login_required
def search_products():
    name = request.args.get("name", "").strip()

    products = Product.query.filter(
        Product.user_id == current_user.id,
        Product.name.ilike(f"%{name}%"),
    ).order_by(Product.id).all()

    return [
        {
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "quantity": product.quantity,
        }
        for product in products
    ]


# --------------------------------------------------
# 9. Customer sales
# --------------------------------------------------

@app.route("/customers/<int:customer_id>/sales")
@login_required
def customer_sales(customer_id):
    customer = get_owned_customer(customer_id)

    if customer is None:
        return {"error": "Customer not found"}, 404

    sales = Sale.query.filter_by(
        customer_id=customer.id,
        user_id=current_user.id,
    ).all()

    return [
        {
            "sale_id": sale.id,
            "product": sale.product.name,
            "quantity": sale.quantity,
        }
        for sale in sales
    ]


# --------------------------------------------------
# 10. Sales API
# --------------------------------------------------

def create_sale_record(customer_id, product_id, quantity):
    """Create a sale safely for the currently logged-in user."""
    try:
        customer = get_owned_customer(customer_id)

        if customer is None:
            return {"error": "Customer not found"}, 404

        product = Product.query.filter_by(
            id=product_id,
            user_id=current_user.id,
        ).with_for_update().first()

        if product is None:
            db.session.rollback()
            return {"error": "Product not found"}, 404

        if product.quantity < quantity:
            available = product.quantity
            db.session.rollback()
            return {
                "error": "Insufficient stock",
                "available_quantity": available,
                "requested_quantity": quantity,
            }, 409

        sale = Sale(
            customer_id=customer.id,
            user_id=current_user.id,
            product_id=product.id,
            quantity=quantity,
        )
        db.session.add(sale)
        db.session.flush()

        item = SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            quantity=quantity,
        )
        db.session.add(item)

        product.quantity -= quantity
        db.session.commit()

        return {
            "message": "Sale created successfully",
            "sale_id": sale.id,
            "customer_id": customer.id,
            "product_id": product.id,
            "quantity_sold": quantity,
            "remaining_stock": product.quantity,
        }, 201

    except IntegrityError:
        db.session.rollback()
        return {
            "error": "Sale could not be saved because of a data conflict"
        }, 409

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Could not create sale")
        return {"error": "Database operation failed"}, 500


@app.route("/sales", methods=["POST"])
@login_required
def create_sale():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {"error": "A JSON object is required"}, 400

    customer_id = data.get("customer_id")
    product_id = data.get("product_id")
    quantity = data.get("quantity")

    if type(customer_id) is not int or customer_id <= 0:
        return {"error": "A valid customer_id is required"}, 400

    if type(product_id) is not int or product_id <= 0:
        return {"error": "A valid product_id is required"}, 400

    if type(quantity) is not int or quantity <= 0:
        return {
            "error": "Quantity must be a positive whole number"
        }, 400

    result, status = create_sale_record(
        customer_id, product_id, quantity
    )
    return result, status


@app.route("/dashboard/sales/create", methods=["POST"])
@login_required
def create_dashboard_sale():
    raw_customer_id = request.form.get("customer_id", "").strip()
    raw_product_id = request.form.get("product_id", "").strip()
    raw_quantity = request.form.get("quantity", "").strip()

    if not (
        raw_customer_id.isdecimal()
        and raw_product_id.isdecimal()
        and raw_quantity.isdecimal()
    ):
        flash(
            "Choose a customer and product, and enter a "
            "positive whole-number quantity.",
            "error",
        )
        return redirect(url_for("dashboard"))

    customer_id = int(raw_customer_id)
    product_id = int(raw_product_id)
    quantity = int(raw_quantity)

    if customer_id <= 0 or product_id <= 0 or quantity <= 0:
        flash(
            "Choose a valid customer and product, and enter "
            "a quantity greater than zero.",
            "error",
        )
        return redirect(url_for("dashboard"))

    result, status = create_sale_record(
        customer_id, product_id, quantity
    )

    if status == 201:
        flash(
            f"Sale #{result['sale_id']} recorded successfully. "
            f"Remaining stock: {result['remaining_stock']}.",
            "success",
        )
    else:
        flash(result.get("error", "Could not record the sale."), "error")

    return redirect(url_for("dashboard"))


@app.route("/sales")
@login_required
def get_sales():
    sales = Sale.query.filter_by(
        user_id=current_user.id,
    ).order_by(Sale.id).all()

    return [
        {
            "id": sale.id,
            "customer": sale.customer.name,
            "product": sale.product.name,
            "quantity": sale.quantity,
        }
        for sale in sales
    ]


@app.route("/sales/customer/<int:customer_id>")
@login_required
def sales_by_customer(customer_id):
    customer = get_owned_customer(customer_id)

    if customer is None:
        return {"error": "Customer not found"}, 404

    sales = Sale.query.filter_by(
        customer_id=customer.id,
        user_id=current_user.id,
    ).all()

    return [
        {
            "customer": sale.customer.name,
            "id": sale.id,
            "product": sale.product.name,
            "quantity": sale.quantity,
        }
        for sale in sales
    ]


@app.route("/sales/<int:sale_id>/receipt")
@login_required
def sale_receipt(sale_id):
    sale = get_owned_sale(sale_id)

    if sale is None:
        return {"error": "Sale not found"}, 404

    return {
        "sale_id": sale.id,
        "customer": sale.customer.name,
        "items": [
            {
                "product": item.product.name,
                "quantity": item.quantity,
                "price": float(item.product.price),
                "subtotal": float(
                    item.product.price * item.quantity
                ),
            }
            for item in sale.items
        ],
    }


# -------------------------------
def parse_report_dates():
    """Validate optional report dates in YYYY-MM-DD format."""
    parsed = []

    for field in ("start_date", "end_date"):
        raw = request.args.get(field, "").strip()

        if not raw:
            parsed.append(None)
            continue

        try:
            value = date.fromisoformat(raw)
        except ValueError:
            return None, None, (
                f"{field} must be a valid date in YYYY-MM-DD format."
            )

        if value.isoformat() != raw:
            return None, None, f"{field} must use YYYY-MM-DD format."

        parsed.append(value)

    start_date, end_date = parsed

    if start_date and end_date and start_date > end_date:
        return None, None, (
            "start_date must be on or before end_date."
        )

    return start_date, end_date, None


def sale_date_filters(start_date=None, end_date=None):
    """Return filters that include the complete selected dates."""
    filters = []

    if start_date:
        filters.append(
            Sale.sale_date >= datetime.combine(start_date, time.min)
        )

    if end_date:
        if end_date == date.max:
            filters.append(Sale.sale_date <= datetime.max)
        else:
            filters.append(
                Sale.sale_date
                < datetime.combine(end_date + timedelta(days=1), time.min)
            )

    return filters


def build_sales_summary(user_id, start_date=None, end_date=None):
    """Calculate sales statistics for one user and optional date range."""
    common_filters = [
        Sale.user_id == user_id,
        *sale_date_filters(start_date, end_date),
    ]

    total_sales = db.session.query(
        func.count(Sale.id)
    ).filter(*common_filters).scalar() or 0

    units_sold = db.session.query(
        func.coalesce(func.sum(Sale.quantity), 0)
    ).filter(*common_filters).scalar() or 0

    estimated_value = db.session.query(
        func.coalesce(func.sum(Sale.quantity * Product.price), 0)
    ).join(
        Product, Sale.product_id == Product.id,
    ).filter(
        *common_filters,
        Product.user_id == user_id,
    ).scalar() or 0

    rows = db.session.query(
        Product.name,
        Product.price,
        func.sum(Sale.quantity).label("units_sold"),
    ).join(
        Sale, Sale.product_id == Product.id,
    ).filter(
        *common_filters,
        Product.user_id == user_id,
    ).group_by(
        Product.id, Product.name, Product.price,
    ).order_by(
        func.sum(Sale.quantity).desc(),
        Product.name.asc(),
    ).limit(10).all()

    top_products = [
        {
            "product": name,
            "units_sold": int(quantity),
            "estimated_value": float(price * quantity),
        }
        for name, price, quantity in rows
    ]

    return {
        "total_sales": int(total_sales),
        "units_sold": int(units_sold),
        "estimated_sales_value": float(estimated_value),
        "top_products": top_products,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
    }


@app.route("/reports/sales-summary")
@login_required
def sales_summary_report():
    start_date, end_date, error = parse_report_dates()

    if error:
        return jsonify({"error": error}), 400

    return build_sales_summary(
        current_user.id,
        start_date=start_date,
        end_date=end_date,
    )


def spreadsheet_safe_text(value):
    """Stop text fields from being treated as spreadsheet formulas."""
    text_value = "" if value is None else str(value)

    if text_value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text_value

    return text_value


@app.route("/reports/sales-export.csv")
@login_required
def sales_export():
    start_date, end_date, error = parse_report_dates()

    if error:
        return jsonify({"error": error}), 400

    rows = db.session.query(
        Sale.id,
        Sale.sale_date,
        Customer.name,
        Product.name,
        Sale.quantity,
        Product.price,
    ).join(
        Customer, Sale.customer_id == Customer.id,
    ).join(
        Product, Sale.product_id == Product.id,
    ).filter(
        Sale.user_id == current_user.id,
        Customer.user_id == current_user.id,
        Product.user_id == current_user.id,
        *sale_date_filters(start_date, end_date),
    ).order_by(
        Sale.sale_date.asc(), Sale.id.asc(),
    ).all()

    output = io.StringIO(newline="")
    writer = csv.writer(output)

    writer.writerow([
        "Sale ID",
        "Sale Date",
        "Customer",
        "Product",
        "Quantity",
        "Current Unit Price (NGN)",
        "Estimated Line Value (NGN)",
    ])

    for sale_id, sale_date, customer, product, quantity, price in rows:
        writer.writerow([
            sale_id,
            sale_date.isoformat(sep=" ") if sale_date else "",
            spreadsheet_safe_text(customer),
            spreadsheet_safe_text(product),
            quantity,
            f"{price:.2f}",
            f"{price * quantity:.2f}",
        ])

    response = Response(
        "\ufeff" + output.getvalue(),
        content_type="text/csv; charset=utf-8",
    )
    response.headers["Content-Disposition"] = (
        'attachment; filename="sales-report.csv"'
    )
    return response




@app.route("/reports")
@login_required
def sales_reports():
    start_date, end_date, error = parse_report_dates()

    start_value = request.args.get("start_date", "").strip()
    end_value = request.args.get("end_date", "").strip()

    if error:
        return render_template(
            "reports.html",
            summary=None,
            error=error,
            start_date_value=start_value,
            end_date_value=end_value,
        ), 400

    summary = build_sales_summary(
        current_user.id,
        start_date=start_date,
        end_date=end_date,
    )

    return render_template(
        "reports.html",
        summary=summary,
        error=None,
        start_date_value=start_value,
        end_date_value=end_value,
    )


@app.route("/reports/sales-count")
@login_required
def sales_count():
    count = db.session.query(
        func.count(Sale.id)
    ).filter(
        Sale.user_id == current_user.id,
    ).scalar()

    return {"total_sales": count}


# --------------------------------------------------
# 12. Dashboard customer creation
# --------------------------------------------------

@app.route("/dashboard/customers/create", methods=["POST"])
@login_required
def create_customer():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()

    if not 2 <= len(name) <= 100:
        flash(
            "Name must be between 2 and 100 characters.",
            "error",
        )
        return redirect(url_for("dashboard"))

    if len(email) > 100 or len(phone) > 20:
        flash("Email or phone is too long.", "error")
        return redirect(url_for("dashboard"))

    if email and (
        "@" not in email
        or "." not in email.rsplit("@", 1)[-1]
    ):
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("dashboard"))

    email = email or None
    phone = phone or None

    try:
        customer = Customer(
            user_id=current_user.id,
            name=name,
            email=email,
            phone=phone,
        )

        db.session.add(customer)
        db.session.commit()

        flash("Customer saved successfully.", "success")

    except IntegrityError:
        db.session.rollback()
        flash(
            "A customer with that email may already exist.",
            "error",
        )

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Could not create customer")
        flash(
            "Could not save the customer. Please try again.",
            "error",
        )

    return redirect(url_for("dashboard"))


# --------------------------------------------------
# 13. Dashboard customer editing
# --------------------------------------------------

@app.route(
    "/dashboard/customers/<int:customer_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit_customer(customer_id):
    customer = get_owned_customer(customer_id)

    if customer is None:
        flash("Customer not found.", "error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip().lower()

        if not 2 <= len(name) <= 100:
            flash(
                "Name must be between 2 and 100 characters.",
                "error",
            )
            return redirect(url_for(
                "edit_customer",
                customer_id=customer.id,
            ))

        if len(phone) > 20 or len(email) > 100:
            flash("Phone or email is too long.", "error")
            return redirect(url_for(
                "edit_customer",
                customer_id=customer.id,
            ))

        if email and (
            "@" not in email
            or "." not in email.rsplit("@", 1)[-1]
        ):
            flash("Please enter a valid email address.", "error")
            return redirect(url_for(
                "edit_customer",
                customer_id=customer.id,
            ))

        customer.name = name
        customer.phone = phone or None
        customer.email = email or None

        try:
            db.session.commit()
            flash("Customer updated successfully.", "success")

        except IntegrityError:
            db.session.rollback()
            flash(
                "A customer with that email may already exist.",
                "error",
            )

        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Could not update customer")
            flash("Could not update the customer.", "error")

        return redirect(url_for("dashboard"))

    return render_template(
        "edit_customer.html",
        customer=customer,
    )


# --------------------------------------------------
# 14. Dashboard customer deletion
# --------------------------------------------------

@app.route(
    "/dashboard/customers/<int:customer_id>/delete",
    methods=["POST"],
)
@login_required
def delete_customer(customer_id):
    customer = get_owned_customer(customer_id)

    if customer is None:
        flash("Customer not found.", "error")
        return redirect(url_for("dashboard"))

    try:
        db.session.delete(customer)
        db.session.commit()
        flash("Customer deleted successfully.", "success")

    except IntegrityError:
        db.session.rollback()
        flash(
            "This customer cannot be deleted while related sales exist.",
            "error",
        )

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Could not delete customer")
        flash("Could not delete the customer.", "error")

    return redirect(url_for("dashboard"))



# --------------------------------------------------
# 15. Product management
# --------------------------------------------------

def parse_product_form():
    """Validate product fields before saving them."""
    name = request.form.get("name", "").strip()
    price_text = request.form.get("price", "").strip()
    quantity_text = request.form.get("quantity", "").strip()

    if not 2 <= len(name) <= 100:
        return None, "Product name must be between 2 and 100 characters."

    try:
        price = Decimal(price_text)
    except (InvalidOperation, ValueError):
        return None, "Enter a valid product price."

    if not price.is_finite() or price <= 0:
        return None, "Price must be greater than zero."

    if price > Decimal("9999999999.99"):
        return None, "Price is too large."

    if price.as_tuple().exponent < -2:
        return None, "Price must have no more than two decimal places."

    try:
        quantity = int(quantity_text)
    except (ValueError, TypeError):
        return None, "Quantity must be a whole number."

    if quantity < 0:
        return None, "Quantity cannot be negative."

    if quantity > 2147483647:
        return None, "Quantity is too large."

    return {
        "name": name,
        "price": price,
        "quantity": quantity,
    }, None


@app.route("/dashboard/products/create", methods=["POST"])
@login_required
def create_product():
    data, error = parse_product_form()

    if error:
        flash(error, "error")
        return redirect(url_for("dashboard"))

    try:
        product = Product(
            user_id=current_user.id,
            name=data["name"],
            price=data["price"],
            quantity=data["quantity"],
        )

        db.session.add(product)
        db.session.commit()

        flash("Product created successfully.", "success")

    except IntegrityError:
        db.session.rollback()
        flash("Could not create the product because of a data conflict.", "error")

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Could not create product")
        flash("Could not save the product. Please try again.", "error")

    return redirect(url_for("dashboard"))


@app.route(
    "/dashboard/products/<int:product_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit_product(product_id):
    product = get_owned_product(product_id)

    if product is None:
        flash("Product not found.", "error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        data, error = parse_product_form()

        if error:
            flash(error, "error")
            return redirect(url_for(
                "edit_product",
                product_id=product.id,
            ))

        product.name = data["name"]
        product.price = data["price"]
        product.quantity = data["quantity"]

        try:
            db.session.commit()
            flash("Product updated successfully.", "success")

        except IntegrityError:
            db.session.rollback()
            flash("Could not update the product because of a data conflict.", "error")

        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Could not update product")
            flash("Could not update the product. Please try again.", "error")

        return redirect(url_for("dashboard"))

    return render_template(
        "edit_product.html",
        product=product,
    )


@app.route(
    "/dashboard/products/<int:product_id>/delete",
    methods=["POST"],
)
@login_required
def delete_product(product_id):
    product = get_owned_product(product_id)

    if product is None:
        flash("Product not found.", "error")
        return redirect(url_for("dashboard"))

    try:
        has_sales = (
            Sale.query.filter_by(product_id=product.id).first() is not None
            or SaleItem.query.filter_by(product_id=product.id).first() is not None
        )

        if has_sales:
            flash(
                "This product has sales history and cannot be deleted. "
                "You can edit its details instead.",
                "error",
            )
            return redirect(url_for("dashboard"))

        db.session.delete(product)
        db.session.commit()
        flash("Product deleted successfully.", "success")

    except IntegrityError:
        db.session.rollback()
        flash(
            "This product is linked to other records and cannot be deleted.",
            "error",
        )

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Could not delete product")
        flash("Could not delete the product. Please try again.", "error")

    return redirect(url_for("dashboard"))


# --------------------------------------------------
# 15. Dashboard
# --------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    q = request.args.get("q", "").strip()

    products = Product.query.filter_by(
        user_id=current_user.id,
    ).order_by(Product.id).all()

    customer_query = Customer.query.filter_by(
        user_id=current_user.id,
    )

    if q:
        search_term = f"%{q}%"

        customer_query = customer_query.filter(
            (Customer.name.ilike(search_term))
            | (Customer.phone.ilike(search_term))
            | (Customer.email.ilike(search_term))
        )

    customers = customer_query.order_by(
        Customer.id,
    ).all()

    total_customers = Customer.query.filter_by(
        user_id=current_user.id,
    ).count()

    total_products = Product.query.filter_by(
        user_id=current_user.id,
    ).count()

    inventory_value = sum(
        float(product.price) * product.quantity
        for product in products
    )

    low_stock_count = Product.query.filter(
        Product.user_id == current_user.id,
        Product.quantity <= 5,
    ).count()

    sale_customers = Customer.query.filter_by(
        user_id=current_user.id,
    ).order_by(Customer.name).all()

    recent_sales = Sale.query.filter_by(
        user_id=current_user.id,
    ).order_by(
        Sale.sale_date.desc(),
        Sale.id.desc(),
    ).limit(10).all()

    sales_summary = build_sales_summary(current_user.id)

    return render_template(
        "index.html",
        products=products,
        customers=customers,
        q=q,
        total_customers=total_customers,
        total_products=total_products,
        inventory_value=inventory_value,
        low_stock_count=low_stock_count,
        sale_customers=sale_customers,
        recent_sales=recent_sales,
        sales_summary=sales_summary,
    )


# --------------------------------------------------
# 16. Registration
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("register.html")

        if len(email) > 120:
            flash("Email is too long.", "error")
            return render_template("register.html")

        if (
            "@" not in email
            or "." not in email.rsplit("@", 1)[-1]
        ):
            flash("Please enter a valid email address.", "error")
            return render_template("register.html")

        if len(password) < 8:
            flash(
                "Password must be at least 8 characters.",
                "error",
            )
            return render_template("register.html")

        existing_user = User.query.filter_by(
            email=email,
        ).first()

        if existing_user:
            flash("That email is already registered.", "error")
            return render_template("register.html")

        user = User(email=email)
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()

            flash(
                "Registration successful. You can now log in.",
                "success",
            )
            return redirect(url_for("login"))

        except IntegrityError:
            db.session.rollback()
            flash("That email is already registered.", "error")

        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Registration failed")
            flash("Registration failed. Please try again.", "error")

    return render_template("register.html")


# --------------------------------------------------
# 17. Login
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and user.is_active and user.check_password(password):
            login_user(user)
            flash("Login successful.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


# --------------------------------------------------
# 18. Logout
# --------------------------------------------------

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have logged out.", "success")
    return redirect(url_for("login"))


# --------------------------------------------------
# 19. Run the application
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
