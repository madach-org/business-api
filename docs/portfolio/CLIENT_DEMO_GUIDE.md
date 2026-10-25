# Client Demo Guide

## Purpose

Use this short walkthrough to explain the Business Management System to a potential small-business client. The deployed demo is at https://business-api-r6vd.onrender.com.

**Safety:** Use an approved demo account and non-sensitive demo records. Do not show passwords, environment variables, database connection strings, private customer details, or other users' records. Avoid creating or deleting live records during a sales presentation unless you have explicit permission and a safe demo dataset.

## Suggested 5–7 minute walkthrough

### 1. Sign in
- Open the live application.
- Explain that business pages require authentication.
- Sign in using an authorized demo account.

### 2. Dashboard
- Show the customer and product counts.
- Explain the inventory value and low-stock indicator.
- Clarify that estimated sales values are calculated using current product prices and may not represent historical prices or audited revenue.

### 3. Customers
- Show the customer list and search.
- Explain that authorized users can manage their customer records.
- Use only approved sample data in a presentation.

### 4. Products and inventory
- Show the product inventory table and edit controls.
- Explain that stock quantities are maintained as sales are recorded.
- Do not change live inventory just to demonstrate the interface.

### 5. Sales
- Show the sale form and recent sales/receipt links.
- Explain that the workflow validates quantities and checks available stock.
- Describe that successful sales reduce stock; do not record a test sale against real inventory.

### 6. Reports
- Show the date-filter form and report summary.
- Demonstrate a report only if the chosen date range is safe and approved.
- Point out the CSV download option.

### 7. Security and deployment
- Briefly describe login protection, record ownership checks, CSRF protection for web forms, PostgreSQL, migrations, and hosted deployment.
- Explain that API routes enforce authentication and return JSON errors where appropriate.

## Questions to ask the client

- How many staff members would use the system?
- Which roles should be allowed to manage customers, products, sales, and reports?
- Do they need invoices, receipts, tax fields, discounts, or multiple branches?
- What backups, exports, and reporting periods do they require?
- Would they prefer a dedicated demo or trial environment?

## Close

Explain that the current project is a working foundation and that any client-specific scope, data migration, integrations, hosting costs, support, and acceptance criteria should be agreed in writing before a commercial deployment.
