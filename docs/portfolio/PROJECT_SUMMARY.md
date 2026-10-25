# Project Summary — Business Management System

A Flask and PostgreSQL business management web application for managing customers, products, inventory, sales, receipts, and sales reports.

- **Live demo:** https://business-api-r6vd.onrender.com
- **GitHub:** https://github.com/madach-org/business-api
- **Stack:** Python, Flask, PostgreSQL, SQLAlchemy, Flask-Migrate/Alembic, Flask-Login, Flask-WTF, Gunicorn, Render, Neon
- **Security:** Authentication, ownership-based access checks, CSRF protection for web forms, and validation of customer, product, and sale inputs.
- **Business logic:** Recording a valid sale reduces available stock; zero-quantity sales and overselling are rejected.
- **Reporting:** Date-filtered sales summary and CSV export.
- **Validation:** Development and acceptance checks covered key workflows; deployed production checks were read-only.

## Short portfolio description

Built and deployed a Flask/PostgreSQL business management system with authenticated customer and product management, inventory-aware sales processing, receipts, and date-filtered CSV reports. Implemented database migrations, validation, CSRF protection, and ownership checks to isolate users' records.

## Resume bullet

Developed and deployed a Flask/PostgreSQL business management application featuring authentication, ownership-based authorization, customer/product CRUD, inventory-aware sales, receipts, and CSV reporting; used SQLAlchemy, Alembic migrations, CSRF protection, and production-safe verification.

## Important wording

Do not describe this as audited accounting software or claim regulatory compliance. Sales value reports use current product prices, so they should not be presented as verified historical revenue without additional price-at-sale records and accounting rules.
