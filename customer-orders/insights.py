"""
This program is meant to demonstrate how to use Python's various data structures like lists, dictionaries, 
and sets to analyze customer orders data. 

SECTION 1: Store customer orders
It will first create a list of customers called customers[].
Next, each customer's order will be saved in a list called orders[], where each order will be a tuple in the list.
This tuple will contain the following information about the order: customer name, product, price, and category.
Finally, the program will create a dictionary called cust_orders{} which will have the customer name as key and 
ordered list of products as values.
"""

# list of customers
customers = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Heidi", "Ivan", "Judy"]

# List of customer orders
orders = [
    ("Alice",   "Novel",        15, "Books"),
    ("Alice",   "T-shirt",      25, "Clothing"),
    ("Bob",     "T-shirt",      25, "Clothing"),
    ("Charlie", "Notebook",     10, "Stationery"),
    ("David",   "Coffee Blend", 22, "Food & Drink"),
    ("Eve",     "Tea Set",      30, "Food & Drink"),
    ("Alice",   "USB Cable",    15, "Electronics"),
    ("Frank",   "Cap",          20, "Clothing"),
    ("Grace",   "Sunglasses",   35, "Accessories"),
    ("Grace",   "SD Card",      50, "Electronics"),
    ("Heidi",   "Tote Bag",     18, "Accessories"),
    ("Alice",   "SD Card",      50, "Electronics"),
    ("Ivan",    "Pen Set",      14, "Stationery"),
    ("Judy",    "Comic Book",   12, "Books"),
    ("Alice",   "Coffee Blend", 22, "Food & Drink"),
    ("Bob",     "Comic Book",   12, "Books"),
    ("Charlie", "T-shirt",      25, "Clothing"),
    ("David",   "Cap",          20, "Clothing"),
    ("Eve",     "Sunglasses",   35, "Accessories"),
    ("Frank",   "Novel",        15, "Books"),
    ("Grace",   "Tea Set",      30, "Food & Drink"),
    ("Heidi",   "Notebook",     10, "Stationery"),
    ("Ivan",    "Tote Bag",     18, "Accessories"),
    ("Judy",    "Pen Set",      14, "Stationery"),
    ("Alice",   "Sunglasses",   35, "Accessories"),
    ("Bob",     "Tea Set",      30, "Food & Drink"),
    ("Bob",     "Cap",          20, "Clothing"),
    ("Charlie", "Comic Book",   12, "Books"),
    ("Ivan",    "Coffee Blend", 22, "Food & Drink"),
    ("Ivan",    "Novel",        15, "Books"),
    ("Judy",    "Sunglasses",   35, "Accessories"),
]

# Create a dictionary to store customer orders
cust_orders = {}
# Loop through each order
for order in orders:
    customer_name = order[0]
    product = order[1]
    
    # If customer name is not already in the dictionary, add it with an empty list
    if customer_name not in cust_orders:
        cust_orders[customer_name] = []
    
    # Append the product to the customer's list of orders
    cust_orders[customer_name].append(product)

# Print the customer orders dictionary
print("Customer Orders:")
for customer, products in cust_orders.items():
    print(f"- {customer}: {products}")
print("\n")

"""SECTION 2: Classify products by category
The program will then create a dictionary called product_category{} which will have the category as key and a values as
lists of ordered products.
It will then display all available product categories.
"""
# Create a dictionary to classify products by category
product_category = {}

# Loop through each order
for order in orders:
    product = order[1]
    category = order[3]

    # If category is not already in the dictionary, add it with an empty list
    if category not in product_category:
        product_category[category] = []

    # Append the product to the category's list of products
    if product not in product_category[category]:
        product_category[category].append(product)

# Print the category products dictionary
print("Product Categories:")
for category, products in product_category.items():
    print(f"- {category}: {products}")
print("\n")

"""SECTION 3: Analyze customer orders
Classify each customer as "High-value buyer" if the total amount spent is above $100.
If total amount is between $50 and $100, then classify as "Moderate buyer".
If total is below $50, classify as "Low-value buyer".
The program will create a dictionary called customer_classification{} which will have the customer name as key and the
classification as value.
Finally, the program will display the classification of each customer.
"""

# Create a dictionary to classify customers based on total amount spent
customer_classification = {}

# Loop through each customer and calculate total amount spent
for customer in customers:
    total_spent = sum(order[2] for order in orders if order[0] == customer)

    # Classify the customer based on total amount spent
    if total_spent > 100:
        customer_classification[customer] = "High-value buyer"
    elif 50 <= total_spent <= 100:
        customer_classification[customer] = "Moderate buyer"
    else:
        customer_classification[customer] = "Low-value buyer"
    
# Print the customer classification dictionary, sorted by classification
print("Customer Classification (high > $100, moderate $50-$100, low < $50):")
print(f"- High-value buyers: {', '.join([customer for customer, classification in customer_classification.items() if classification == 'High-value buyer'])}")
print(f"- Moderate buyers: {', '.join([customer for customer, classification in customer_classification.items() if classification == 'Moderate buyer'])}")
print(f"- Low-value buyers: {', '.join([customer for customer, classification in customer_classification.items() if classification == 'Low-value buyer'])}")
print("\n")

"""
SECTION 4: Generate business insights
The program will create a dictionary called category_sales{} which will have the category as key and total sales 
amount as value.
Then it will extract unique products from all orders using sets and display them.
Then, use list comprehension to find all customers who purchased electronics.
Finally, the program will display the top three highest spending customers using sorting.
"""

# Create a dictionary to calculate total sales for each category
category_sales = {} 

# Loop through each order and calculate total sales for each category
for order in orders:
    category = order[3]
    price = order[2]

    if category not in category_sales:
        category_sales[category] = 0
    category_sales[category] += price

# Print the category sales dictionary
print("Total revenue per product category:")
for category, sales in category_sales.items():
    print(f"- {category}: ${sales}")
print("\n")

# Extract unique products from all orders using a set
unique_products = set(order[1] for order in orders)
print("Unique Products:\n- " + "\n- ".join(sorted(unique_products)))
print("\n")

# List all customers who purchased at least one electronics item using list comprehension
electronics_customers = set([order[0] for order in orders if order[3] == "Electronics"])
print("Customers who purchased electronics: \n- " + "\n- ".join(sorted(electronics_customers)))
print("\n")

# Show top 3 customers by amount spent
# First create a dictionary to calculate total amount spent by each customer
customer_spending = {}
for order in orders:
    customer_name = order[0]
    price = order[2]

    if customer_name not in customer_spending:
        customer_spending[customer_name] = 0
    customer_spending[customer_name] += price

# Sort customers by total spending and get the top 3
top_customers = sorted(customer_spending.items(), key=lambda x: x[1], reverse=True)[:3]
print("Top 3 highest spending customers:\n- " + "\n- ".join([f"{customer}: ${total}" for customer, total in top_customers]))
print("\n")

"""
SECTION 5: Organize and display data
Print a summary of each customer's total spending and classification.
Demonstrate how to find customers who purchased from multiple categories using sets.
Finally, print list of customers who purchased from both electronics and clothing categories.
"""

# Print a summary of each customer's total spending and classification
print("\nCustomer Summary:")  
for customer in customers:
    total_spent = customer_spending[customer]
    classification = customer_classification[customer]
    print(f"- {customer}: ${total_spent}, {classification}")
print("\n")

# Find customers who purchased from multiple categories using sets
customer_order_categories = {}
for order in orders:
    customer_name = order[0]
    category = order[3]

    if customer_name not in customer_order_categories:
        customer_order_categories[customer_name] = set()
    customer_order_categories[customer_name].add(category)

# List customers who purchased from multiple categories
print("Customers who purchased from multiple categories:")
for customer, categories in customer_order_categories.items():
    if len(categories) > 1:
        print(f"- {customer}: {', '.join(categories)}") 
print("\n")

# List customers who purchased from both electronics and clothing categories
print("Customers who purchased from both Electronics and Clothing categories:")
for customer, categories in customer_order_categories.items():
    if "Electronics" in categories and "Clothing" in categories:
        print(f"- {customer}")  
print("\n")