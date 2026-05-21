# Customer Orders Analysis

A Python script that analyzes customer order data using core data structures: lists, dictionaries, tuples, and sets.

## How to Run

```
python customer-orders/insights.py
```

## What It Does

The script works through five analysis tasks against a fixed dataset of 30 orders across 10 customers.

### Task 1 — Store Customer Orders
Builds a dictionary (`cust_orders`) mapping each customer name to a sorted list of products they ordered.

### Task 2 — Classify Products by Category
Groups unique products into six categories: Books, Clothing, Stationery, Food & Drink, Electronics, and Accessories.

### Task 3 — Analyze Customer Spending
Calculates each customer's total spend and classifies them:
- **High-value buyer** — over $100
- **Moderate buyer** — $50–$100
- **Low-value buyer** — under $50

### Task 4 — Generate Business Insights
- Total revenue per product category
- Unique products across all orders (using a `set`)
- Customers who purchased Electronics (using list comprehension)
- Top 3 highest-spending customers

### Task 5 — Organize and Display Data
- Full customer summary (total spend + classification)
- Customers who purchased from more than one category
- Customers who purchased from both Electronics and Clothing

## Sample Output
Full sample output is saved in [output.txt](output.txt).

## Concepts Demonstrated

- Lists — customers[], orders[], and per-customer product lists
- Tuples — each order entry in orders[] (name, product, price, category)
- Dictionaries — cust_orders, product_category, customer_classification, category_sales, customer_spending
- Sets — unique products across all orders, and per-customer category sets
- List comprehension — filtering customers who purchased Electronics
- Sorting — top 3 customers by spend, using sorted() with a lambda key
- String formatting — all output uses f-strings
