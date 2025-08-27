import re
import decimal
import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Customer, Product, Order
from .filters import CustomerFilter, ProductFilter, OrderFilter

PHONE_REGEX = re.compile(r"^(\+?\d[\d\-]{6,}\d)$")

# GraphQL Types
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        interfaces = (relay.Node,)
        filterset_class = CustomerFilter

class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        interfaces = (relay.Node,)
        filterset_class = ProductFilter

class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (relay.Node,)
        filterset_class = OrderFilter

# Inputs
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)

class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int(required=False, default_value=0)

class CreateCustomerPayload(graphene.ObjectType):
    customer = graphene.Field(CustomerType)
    message = graphene.String()
    errors = graphene.List(graphene.String)

class BulkCreateCustomersPayload(graphene.ObjectType):
    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

class CreateProductPayload(graphene.ObjectType):
    product = graphene.Field(ProductType)
    errors = graphene.List(graphene.String)

class CreateOrderPayload(graphene.ObjectType):
    order = graphene.Field(OrderType)
    errors = graphene.List(graphene.String)

# Mutations
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    Output = CreateCustomerPayload

    @staticmethod
    def mutate(root, info, input: CustomerInput):
        errs = []
        # Email uniqueness
        if Customer.objects.filter(email=input.email).exists():
            errs.append("Email already exists")
        # Phone format
        if input.phone and not PHONE_REGEX.match(input.phone):
            errs.append("Invalid phone format")
        if errs:
            return CreateCustomerPayload(customer=None, message=None, errors=errs)
        customer = Customer.objects.create(name=input.name, email=input.email, phone=input.phone or "")
        return CreateCustomerPayload(customer=customer, message="Customer created", errors=[])

class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CustomerInput, required=True)

    Output = BulkCreateCustomersPayload

    @staticmethod
    def mutate(root, info, input):
        created = []
        errors = []
        with transaction.atomic():
            for idx, item in enumerate(input, start=1):
                errs = []
                if Customer.objects.filter(email=item.email).exists():
                    errs.append(f"Row {idx}: Email already exists")
                if item.phone and not PHONE_REGEX.match(item.phone):
                    errs.append(f"Row {idx}: Invalid phone format")
                if not item.name:
                    errs.append(f"Row {idx}: Name is required")
                if not item.email:
                    errs.append(f"Row {idx}: Email is required")

                if errs:
                    errors.extend(errs)
                    continue
                c = Customer(name=item.name, email=item.email, phone=item.phone or "")
                c.save()
                created.append(c)
        return BulkCreateCustomersPayload(customers=created, errors=errors)

class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)
    Output = CreateProductPayload

    @staticmethod
    def mutate(root, info, input: ProductInput):
        errors = []
        try:
            price = decimal.Decimal(str(input.price))
            if price <= 0:
                errors.append("Price must be positive")
        except Exception:
            errors.append("Invalid price")

        stock = input.stock or 0
        if stock < 0:
            errors.append("Stock cannot be negative")

        if errors:
            return CreateProductPayload(product=None, errors=errors)

        p = Product.objects.create(name=input.name, price=price, stock=stock)
        return CreateProductPayload(product=p, errors=[])

class CreateOrder(graphene.Mutation):
    class Arguments:
        customer_id = graphene.ID(required=True)
        product_ids = graphene.List(graphene.ID, required=True)
        order_date = graphene.DateTime(required=False)

    Output = CreateOrderPayload

    @staticmethod
    def mutate(root, info, customer_id, product_ids, order_date=None):
        errors = []
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            errors.append("Invalid customer ID")
            return CreateOrderPayload(order=None, errors=errors)

        if not product_ids:
            errors.append("At least one product must be provided")
            return CreateOrderPayload(order=None, errors=errors)

        products = list(Product.objects.filter(pk__in=product_ids))
        missing = set(map(int, product_ids)) - set(p.id for p in products)
        if missing:
            errors.append(f"Invalid product ID(s): {', '.join(map(str, sorted(missing)))}")
            return CreateOrderPayload(order=None, errors=errors)

        if order_date is None:
            order_date = timezone.now()

        with transaction.atomic():
            order = Order.objects.create(customer=customer, order_date=order_date)
            order.products.set(products)
            # Calculate total
            total = sum(p.price for p in products)
            order.total_amount = total
            order.save(update_fields=["total_amount"])
        return CreateOrderPayload(order=order, errors=[])

# Query with filtering and ordering
ALLOWED_CUSTOMER_ORDER_FIELDS = ["name", "-name", "email", "-email", "created_at", "-created_at"]
ALLOWED_PRODUCT_ORDER_FIELDS = ["name", "-name", "price", "-price", "stock", "-stock", "created_at", "-created_at"]
ALLOWED_ORDER_ORDER_FIELDS = ["order_date", "-order_date", "total_amount", "-total_amount", "created_at", "-created_at"]

class Query(graphene.ObjectType):
    hello = graphene.String()

    all_customers = DjangoFilterConnectionField(
        CustomerType,
        order_by=graphene.String(required=False),
    )
    all_products = DjangoFilterConnectionField(
        ProductType,
        order_by=graphene.String(required=False),
    )
    all_orders = DjangoFilterConnectionField(
        OrderType,
        order_by=graphene.String(required=False),
    )

    def resolve_hello(root, info):
        return "Hello, GraphQL!"

    def resolve_all_customers(root, info, order_by=None, **kwargs):
        qs = Customer.objects.all()
        if order_by in ALLOWED_CUSTOMER_ORDER_FIELDS:
            qs = qs.order_by(order_by)
        return qs

    def resolve_all_products(root, info, order_by=None, **kwargs):
        qs = Product.objects.all()
        if order_by in ALLOWED_PRODUCT_ORDER_FIELDS:
            qs = qs.order_by(order_by)
        return qs

    def resolve_all_orders(root, info, order_by=None, **kwargs):
        qs = Order.objects.all().distinct()
        if order_by in ALLOWED_ORDER_ORDER_FIELDS:
            qs = qs.order_by(order_by)
        return qs

class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
