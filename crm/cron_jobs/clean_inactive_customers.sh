#!/bin/bash
# Script to delete inactive customers (no orders in past year)

timestamp=$(date "+%Y-%m-%d %H:%M:%S")
deleted_count=$(echo "
from datetime import timedelta
from django.utils import timezone
from crm.models import Customer

cutoff = timezone.now() - timedelta(days=365)
qs = Customer.objects.filter(orders__isnull=True) | Customer.objects.exclude(orders__order_date__gte=cutoff)
count = qs.distinct().delete()[0]
print(count)
" | python manage.py shell 2>/dev/null)

echo "$timestamp - Deleted $deleted_count inactive customers" >> /tmp/customer_cleanup_log.txt
