import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alx_backend_graphql_crm.settings")
django.setup()

from crm.models import Customer, Product

def seed():
    # Seed Customers
    customers = [
        {"name": "Alice", "email": "alice@example.com", "phone": "+123456789"},
        {"name": "Bob", "email": "bob@example.com", "phone": "123-456-7890"},
        {"name": "Carol", "email": "carol@example.com", "phone": None},
    ]
    for c in customers:
        Customer.objects.get_or_create(email=c["email"], defaults=c)

    # Seed Products
    products = [
        {"name": "Laptop", "price": 999.99, "stock": 10},
        {"name": "Phone", "price": 499.99, "stock": 20},
        {"name": "Headphones", "price": 99.99, "stock": 50},
    ]
    for p in products:
        Product.objects.get_or_create(name=p["name"], defaults=p)

    print("✅ Database seeded successfully!")

if __name__ == "__main__":
    seed()
