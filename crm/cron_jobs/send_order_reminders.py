#!/usr/bin/env python3
import requests
import datetime

GRAPHQL_ENDPOINT = "http://localhost:8000/graphql"
query = """
query RecentOrders {
  allOrders {
    id
    customer {
      email
    }
    orderDate
  }
}
"""

def main():
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=7)

    response = requests.post(GRAPHQL_ENDPOINT, json={"query": query})
    data = response.json()

    orders = data.get("data", {}).get("allOrders", [])
    with open("/tmp/order_reminders_log.txt", "a") as f:
        for order in orders:
            order_date = datetime.datetime.fromisoformat(order["orderDate"]).date()
            if order_date >= cutoff:
                log = f"{datetime.datetime.now()} - Reminder for Order {order['id']} (Customer: {order['customer']['email']})"
                f.write(log + "\n")

    print("Order reminders processed!")

if __name__ == "__main__":
    main()
