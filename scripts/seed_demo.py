"""Create the three role accounts and three demonstration workflows.

The script is idempotent: existing named demo records are reused and completed
workflows are not posted twice.
"""

from datetime import date, timedelta
from pathlib import Path
import sys

from werkzeug.security import generate_password_hash

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from database import connect


ADMIN = ("Mohith", "jmohith@gmail.com", "Mohith@2912")
ACCOUNTANT = ("Mohith DH", "jmohith2912@gmail.com", "Accounts@2912")
CUSTOMER = ("Demo Customer", "demo.customer@urbanfurniture.in", "Customer@2912")


app = create_app()
client = app.test_client()


def session():
    return client.get("/api/session").get_json()


def send(path, payload, method="POST"):
    response = client.open(
        f"/api{path}",
        method=method,
        json=payload,
        headers={"X-CSRF-Token": session()["csrf"]},
    )
    if response.status_code >= 400:
        raise RuntimeError(f"{path}: {response.status_code} {response.get_data(as_text=True)}")
    return response.get_json()


initial = session()
if initial["needs_setup"]:
    send("/setup", {"name": ADMIN[0], "email": ADMIN[1], "password": ADMIN[2]})

with connect(app.config["DATABASE"]) as database:
    database.execute(
        "UPDATE users SET password=?,active=1 WHERE email=?",
        (generate_password_hash(ADMIN[2]), ADMIN[1]),
    )
    database.execute(
        "UPDATE users SET password=?,active=1 WHERE email=?",
        (generate_password_hash(ACCOUNTANT[2]), ACCOUNTANT[1]),
    )

send("/login", {"email": ADMIN[1], "password": ADMIN[2]})


def workspace_data():
    response = client.get("/api/data")
    if response.status_code != 200:
        raise RuntimeError(response.get_data(as_text=True))
    return response.get_json()


data = workspace_data()
contacts = {item["name"]: item for item in data.get("contacts", [])}
contact_specs = [
    {
        "name": "Demo Customer Bengaluru",
        "type": "Customer",
        "email": CUSTOMER[1],
        "mobile": "9876543210",
        "gstin": "29ABCDE1234F1Z5",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560001",
        "address": "12 MG Road, Bengaluru",
        "image": "",
        "portal_password": CUSTOMER[2],
    },
    {
        "name": "Demo Timber Supplies",
        "type": "Vendor",
        "email": "demo.vendor@urbanfurniture.in",
        "mobile": "9876501234",
        "gstin": "29AACCD1234E1Z7",
        "city": "Mysuru",
        "state": "Karnataka",
        "pincode": "570001",
        "address": "Industrial Estate, Mysuru",
        "image": "",
    },
]
for payload in contact_specs:
    if payload["name"] not in contacts:
        send("/masters/contacts", payload)

data = workspace_data()
contacts = {item["name"]: item for item in data["contacts"]}
users = {item["email"]: item for item in data.get("users", [])}
if ACCOUNTANT[1] not in users:
    send("/users", {"name": ACCOUNTANT[0], "email": ACCOUNTANT[1], "password": ACCOUNTANT[2], "role": "accountant"})
if CUSTOMER[1] not in users:
    send("/users", {"name": CUSTOMER[0], "email": CUSTOMER[1], "password": CUSTOMER[2], "role": "contact", "contact_id": contacts["Demo Customer Bengaluru"]["id"]})

product_specs = [
    ("Oslo Lounge Chair", "CHAIR-OSLO", "Living Room", "12500", "7200", "9401", "Nos", "4"),
    ("Nova Study Desk", "DESK-NOVA", "Office", "18900", "11200", "9403", "Nos", "3"),
    ("Aura Sofa Set", "SOFA-AURA", "Living Room", "48500", "32000", "9401", "Set", "2"),
]
data = workspace_data()
products = {item["name"]: item for item in data.get("products", [])}
for name, sku, category, sales_price, cost, hsn, unit, reorder_level in product_specs:
    if name not in products:
        send("/masters/products", {"name": name, "sku": sku, "type": "Goods", "category": category, "sales_price": sales_price, "cost": cost, "hsn": hsn, "unit": unit, "reorder_level": reorder_level})

data = workspace_data()
products = {item["name"]: item for item in data["products"]}
journals = {item["type"]: item for item in data["journals"] if item["active"]}
today = date.today()
due = (today + timedelta(days=30)).isoformat()

if not any(order.get("notes") == "Demo workflow 1: stock purchase" for order in data.get("orders", [])):
    purchase = send("/orders", {
        "kind": "purchase", "contact_id": contacts["Demo Timber Supplies"]["id"], "journal_id": journals["Purchase"]["id"],
        "date": today.isoformat(), "due_date": due, "tax_mode": "intra", "place_of_supply": "Karnataka",
        "notes": "Demo workflow 1: stock purchase",
        "lines": [{"product_id": products[name]["id"], "quantity": "10", "unit_price": cost, "tax_rate": "18"} for name, _sku, _category, _sales, cost, _hsn, _unit, _reorder in product_specs],
    })
    send(f"/orders/{purchase['id']}/post", {"date": today.isoformat(), "due_date": due})

data = workspace_data()
if not any(order.get("notes") == "Demo workflow 2: GST customer sale" for order in data.get("orders", [])):
    sale = send("/orders", {
        "kind": "sale", "contact_id": contacts["Demo Customer Bengaluru"]["id"], "journal_id": journals["Sales"]["id"],
        "date": today.isoformat(), "due_date": due, "tax_mode": "intra", "place_of_supply": "Karnataka",
        "notes": "Demo workflow 2: GST customer sale",
        "lines": [
            {"product_id": products["Oslo Lounge Chair"]["id"], "quantity": "2", "unit_price": "12500", "tax_rate": "18"},
            {"product_id": products["Nova Study Desk"]["id"], "quantity": "1", "unit_price": "18900", "tax_rate": "18"},
        ],
    })
    posted = send(f"/orders/{sale['id']}/post", {"date": today.isoformat(), "due_date": due})
    invoice = next(item for item in workspace_data()["documents"] if item["id"] == posted["id"])
    send(f"/documents/{invoice['id']}/payments", {"amount": f"{invoice['total'] / 200:.2f}", "date": today.isoformat(), "method": "Bank", "reference": "DEMO-PARTIAL-PAYMENT"})

data = workspace_data()
if not any(item.get("name") == "Demo workflow 3: showroom lighting" for item in data.get("expenses", [])):
    account = next(item for item in data["accounts"] if item["code"] == "5100" and item["active"])
    send("/expenses", {"name": "Demo workflow 3: showroom lighting", "date": today.isoformat(), "amount": "8500", "method": "Bank", "account_id": account["id"], "analytic_id": "", "reference": "DEMO-EXPENSE"})

final = workspace_data()
print(f"Demo ready: {len(final['products'])} products, {len(final['documents'])} documents, {len(final['expenses'])} expenses, {len(final.get('users', []))} users")
