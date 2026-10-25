# Business Management System — Case Study

## Overview

The Business Management System is a web application for small businesses to manage customers, products, inventory, sales, and sales reports from one authenticated dashboard.

**Live application:** https://business-api-r6vd.onrender.com  
**Source repository:** https://github.com/madach-org/business-api

## The problem

Small businesses can struggle when customer records, product quantities, and sales information are maintained in separate places. This project brings those common workflows into one web application and provides a central place to review business activity.

## The solution

The application provides a dashboard and protected workflows for managing customer and product records, recording sales, keeping inventory quantities in sync, viewing receipts, and filtering sales reports by date. It also provides CSV report downloads.

## Key capabilities

- User registration and login.
- Authenticated dashboard.
- Customer creation, editing, deletion, and search.
- Product and inventory management.
- Sale recording with quantity validation and stock reduction.
- Sales list and receipt view.
- Sales reports with date filters and CSV export.
- User ownership checks to prevent users from accessing another user's records.
- API endpoints that return JSON responses and enforce authentication.
- Database migrations for schema changes.

## Technology

- **Backend:** Python, Flask
- **Database access:** Flask-SQLAlchemy and SQLAlchemy
- **Database:** PostgreSQL
- **Schema migrations:** Flask-Migrate / Alembic
- **Authentication:** Flask-Login
- **Request protection:** Flask-WTF CSRF protection
- **Production server:** Gunicorn
- **Deployment:** Render application hosting and Neon PostgreSQL

## Engineering considerations

### Data integrity

The sale workflow validates requested quantities and checks available stock before recording a sale. Successful sales update inventory. Tests covered rejection of zero-quantity sales and overselling, and checks covered that rejected operations did not alter stock or create invalid records.

### Access control

The application uses login protection and ownership checks for business records. Testing covered cross-user access attempts, including attempts to use another user's customer or product.

### Production safety

The deployed application was checked using read-only requests for key pages and authentication behaviour. The live database contains real inventory data, so destructive tests and live sale tests were deliberately not repeated in production.

## Validation performed

Development and acceptance checks covered authentication, protected routes, customer validation, user ownership, product validation, sale validation, inventory updates, receipts, and reporting. Read-only production checks verified key pages and API authentication responses.

This summary distinguishes development/acceptance tests from production checks; it does not claim every workflow was re-run against the live database.

## Screenshots

Screenshots are included in [`screenshots/`](screenshots/). Customer table rows and the recent-sale row have been blurred in the portfolio copies to reduce exposure of personal or record-level data.

- [Dashboard overview](screenshots/01-dashboard-overview.png)
- [Dashboard summary](screenshots/02-dashboard-summary.png)
- [Customer management](screenshots/03-customer-management.png)
- [Customer search](screenshots/04-customer-search.png)
- [Product inventory](screenshots/05-product-inventory.png)
- [Product and sale forms](screenshots/06-product-and-sale-forms.png)
- [Sales recording](screenshots/07-sales-recording.png)
- [Report filters](screenshots/08-sales-report-filters.png)
- [Report date range](screenshots/09-sales-report-date-range.png)
- [Report results](screenshots/10-sales-report-results.png)
- [Login page](screenshots/11-login-page.png)

## Current limitations and next improvements

Possible future improvements include automated continuous integration, expanded automated regression coverage, API documentation, monitoring, structured production logging, and a dedicated demo environment seeded with synthetic data.

## Summary

This project demonstrates practical full-stack backend engineering: authenticated workflows, relational data modelling, validation, inventory integrity, ownership-based authorization, database migrations, production deployment, and documentation.
