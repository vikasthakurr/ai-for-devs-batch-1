"""
Seed script to create and populate the e-commerce SQLite database.
Run this once: python seed_db.py
"""
import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "ecommerce.db"


def create_tables(cursor):
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            city TEXT NOT NULL,
            joined_date TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            status TEXT NOT NULL,
            total_amount REAL NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    """)


def seed_data(cursor):
    # Customers
    cities = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Pune", "Kolkata", "Jaipur"]
    customers = []
    for i in range(1, 51):
        name = f"Customer_{i}"
        email = f"customer{i}@example.com"
        city = random.choice(cities)
        joined = (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 500))).strftime("%Y-%m-%d")
        customers.append((name, email, city, joined))

    cursor.executemany(
        "INSERT INTO customers (name, email, city, joined_date) VALUES (?, ?, ?, ?)",
        customers
    )

    # Products
    products = [
        ("Wireless Mouse", "Electronics", 599.0, 150),
        ("Bluetooth Headphones", "Electronics", 1499.0, 80),
        ("USB-C Hub", "Electronics", 2199.0, 60),
        ("Laptop Stand", "Accessories", 899.0, 100),
        ("Mechanical Keyboard", "Electronics", 3499.0, 45),
        ("Webcam HD", "Electronics", 1999.0, 70),
        ("Phone Case", "Accessories", 299.0, 200),
        ("Screen Protector", "Accessories", 199.0, 300),
        ("Power Bank 10000mAh", "Electronics", 1299.0, 90),
        ("Smartwatch", "Electronics", 4999.0, 35),
        ("Cotton T-Shirt", "Clothing", 499.0, 250),
        ("Running Shoes", "Footwear", 2999.0, 60),
        ("Backpack", "Accessories", 1599.0, 80),
        ("Water Bottle", "Kitchen", 399.0, 180),
        ("Yoga Mat", "Fitness", 799.0, 120),
    ]
    cursor.executemany(
        "INSERT INTO products (name, category, price, stock) VALUES (?, ?, ?, ?)",
        products
    )

    # Orders and Order Items
    statuses = ["delivered", "shipped", "processing", "cancelled"]
    for _ in range(200):
        customer_id = random.randint(1, 50)
        order_date = (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d")
        status = random.choice(statuses)

        # Pick 1-4 products for this order
        num_items = random.randint(1, 4)
        chosen_products = random.sample(range(1, 16), num_items)

        total = 0.0
        items = []
        for pid in chosen_products:
            qty = random.randint(1, 3)
            price = products[pid - 1][2]
            items.append((pid, qty, price))
            total += price * qty

        cursor.execute(
            "INSERT INTO orders (customer_id, order_date, status, total_amount) VALUES (?, ?, ?, ?)",
            (customer_id, order_date, status, round(total, 2))
        )
        order_id = cursor.lastrowid

        for pid, qty, price in items:
            cursor.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                (order_id, pid, qty, price)
            )


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Drop existing tables for a fresh seed
    cursor.executescript("""
        DROP TABLE IF EXISTS order_items;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS customers;
    """)

    create_tables(cursor)
    seed_data(cursor)
    conn.commit()
    conn.close()
    print("Database seeded successfully with e-commerce data!")
    print("Tables: customers (50), products (15), orders (200), order_items (varied)")


if __name__ == "__main__":
    main()
