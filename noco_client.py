import os
import requests
from dotenv import load_dotenv
from datetime import datetime
import uuid
import threading
import json
import time
import re


monthly_data = []
data_needs_update = True
data_thread = None

# Load environment variables
load_dotenv()

NOCODB_API_URL = os.getenv("NOCODB_API_URL").rstrip("/")
NOCODB_API_TOKEN = os.getenv("NOCODB_API_TOKEN")
BASE_ID = os.getenv("NOCODB_BASE_ID")

headers = {
    "xc-token": NOCODB_API_TOKEN,
    "Content-Type": "application/json"
}

def get_table(base_id, table_name):
    url = f"{NOCODB_API_URL}/api/v2/meta/bases/{base_id}/tables"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"Failed to list tables: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    if isinstance(data, dict) and "list" in data:
        tables = data["list"]
    else:
        tables = data
    for t in tables:
        if isinstance(t, dict) and t.get("table_name") == table_name:
            return t
    return None

def create_table(base_id, table_name):
    """Create a new table in the specified base with the given table name."""
    url = f"{NOCODB_API_URL}/api/v2/meta/bases/{base_id}/tables"
    # Define the payload for creating a new table
    # Ensure the primary key is set for the uuid column
    payload = {
        "columns": [
            {
                "type": "SingleLineText",
                "title": "uuid",
                "pk": True  # <-- Set as primary key
            },
            {"uidt": "SingleLineText", "title": "unique_id"},
            {"uidt": "SingleLineText", "title": "name"},
            {"uidt": "SingleLineText", "title": "quantity"},
            {
                "uidt": "Currency",
                "title": "unit_price",
                "meta": {
                    "currency_code": "AZN",
                    "currency_locale": "az-AZ"
                }
            },
            {"uidt": "SingleLineText", "title": "date"},
            {
                "uidt": "Currency",
                "title": "total_price",
                "meta": {
                    "currency_code": "AZN",
                    "currency_locale": "az-AZ"
                }
            }
        ],
        "table_name": table_name,
        "title": table_name
    }
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code in (200, 201):
        print(f"Table created: {table_name}")
        return resp.json()
    else:
        print(f"Failed to create table: {resp.status_code} {resp.text}")
        return None


def add_row_to_table(table_id, item):
    url = f"{NOCODB_API_URL}/api/v2/tables/{table_id}/records"
    resp = requests.post(url, headers=headers, json=item)
    if resp.status_code in (200, 201):
        print(f"Row inserted: {resp.json()}")
    else:
        print(f"Failed to insert row: {resp.status_code} {resp.text}")


def get_table_record_count(table_id, where=None):
    """
    Returns the count of records in the table.
    Optionally accepts a 'where' filter string.
    """
    count_url = f"{NOCODB_API_URL}/api/v2/tables/{table_id}/records/count"
    params = {}
    if where:
        params["where"] = where
    resp = requests.get(count_url, headers=headers, params=params)
    if resp.status_code != 200:
        print(f"Failed to get count: {resp.status_code} {resp.text}")
        return 0
    return resp.json().get("count", 0)


def store_receipt_items(item):
    """
    Store a receipt item in the appropriate NocoDB table.
    The table is determined by the item's date (YYYY_MM).
    """
    global data_needs_update # Flag to indicate if data needs to be updated

    # Try to extract year, month, and day from item's date
    date_str = item.get("date")
    table_name = None
    unique_id = None
    if date_str:
        # Normalize date: replace dots and slashes with dashes, remove seconds if present
        date_str = date_str.replace('.', '-')
        date_str = date_str.replace("/", "-")  # Replace colons with dashes for consistency
        # Remove seconds if present (keep only up to minutes)
        if len(date_str) > 16 and ":" in date_str:
            date_str = date_str[:16]
        # Match dd-mm-yyyy or d-m-yyyy
        date_match = re.match(r"(\d{1,2})-(\d{1,2})-(\d{4})", date_str)
        if date_match:
            day, month, year = date_match.groups()
            table_name = f"items_{year}_{month.zfill(2)}"
            unique_id = str(int(day))  # Always store as string, remove leading zeros
    if not table_name:
        # Fallback to current month if date is missing or invalid
        table_name = f"items_{datetime.now().strftime('%Y_%m')}"
        unique_id = str(datetime.now().day)

    print(f"Using data to store in nocodb in received format is: {item}")

    # Ensure the item has a unique uuid for the primary key
    item = dict(item)  # Make a copy to avoid mutating the original
    item["uuid"] = str(uuid.uuid4())
    item["unique_id"] = unique_id  # Set unique_id as day of month

    table = get_table(BASE_ID, table_name)
    if table:
        print(f"Table already exists: {table_name}")
        table_id = table["id"]
    else:
        new_table = create_table(BASE_ID, table_name)
        if not new_table:
            exit("Table creation failed. Exiting.")
        table_id = new_table["id"]

    add_row_to_table(table_id, item)
    data_needs_update = True  # Set flag to True when new data is added


from datetime import datetime, timedelta
import requests

def safe_float_conversion(value, default=0.0):
    """Safely convert a value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def get_week_total_price_list(table_id):
    try:
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        days_of_week = [(start_of_week + timedelta(days=i)).day for i in range(7)]
        days_of_week_str = [str(day) for day in days_of_week]

        # Build the 'where' query for unique_id in days_of_week_str
        where = f"(unique_id,in,{','.join(days_of_week_str)})"
        fields = "total_price"

        # Get the count of records for the week
        count_url = f"{NOCODB_API_URL}/api/v2/tables/{table_id}/records/count"
        count_params = {"where": where}
        count_resp = requests.get(count_url, headers=headers, params=count_params)
        if count_resp.status_code != 200:
            print(f"Failed to get count: {count_resp.status_code} {count_resp.text}")
            return 0.0

        count = count_resp.json().get("count", 100)

        url = f"{NOCODB_API_URL}/api/v2/tables/{table_id}/records"
        params = {
            "where": where,
            "fields": fields,
            "limit": count,
            "offset": 0
        }
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            print(f"Failed to get records: {resp.status_code} {resp.text}")
            return 0.0

        data = resp.json()
        records = data["list"] if "list" in data else data
        prices = [safe_float_conversion(row.get("total_price")) for row in records]
        return round(sum(prices), 2)
    except Exception as e:
        print(f"Error calculating week total: {str(e)}")
        return 0.0

# Example usage:
# prices = get_week_total_price_list("m689rrvk511ux6y")
# print("All total_prices for current week:", prices)
# print("Sum for week:", sum(prices))

def get_month_total_price():
    """
    Get the sum of total_price for all records in the current month's table.
    """
    try:
        table_name = f"items_{datetime.now().strftime('%Y_%m')}"
        table = get_table(BASE_ID, table_name)
        if not table:
            print(f"No table found for this month: {table_name}")
            return 0.0
        
        table_id = table["id"]
        count = get_table_record_count(table_id)
        
        url = f"{NOCODB_API_URL}/api/v2/tables/{table_id}/records"
        params = {"fields": "total_price", "limit": count, "offset": 0}
        resp = requests.get(url, headers=headers, params=params)
        
        if resp.status_code != 200:
            print(f"Failed to get records: {resp.status_code} {resp.text}")
            return 0.0
            
        data = resp.json()
        records = data["list"] if "list" in data else data
        prices = [safe_float_conversion(row.get("total_price")) for row in records]
        return round(sum(prices), 2)
    except Exception as e:
        print(f"Error calculating month total: {str(e)}")
        return 0.0



def get_today_total_price():
    """
    Get the sum of total_price for all records for today in the current month's table.
    """
    try:
        from datetime import datetime
        
        table_name = f"items_{datetime.now().strftime('%Y_%m')}"
        table = get_table(BASE_ID, table_name)
        if not table:
            print(f"No table found for this month: {table_name}")
            return 0.0
        
        table_id = table["id"]
        today_day = str(datetime.now().day)
        
        # Build the 'where' query for today's unique_id
        where = f"(unique_id,eq,{today_day})"
        fields = "total_price"
        
        # Get the count of records for today
        count = get_table_record_count(table_id, where)
        
        url = f"{NOCODB_API_URL}/api/v2/tables/{table_id}/records"
        params = {
            "where": where,
            "fields": fields,
            "limit": count,
            "offset": 0
        }
        resp = requests.get(url, headers=headers, params=params)
        
        if resp.status_code != 200:
            print(f"Failed to get records: {resp.status_code} {resp.text}")
            return 0.0
            
        data = resp.json()
        records = data["list"] if "list" in data else data
        prices = [safe_float_conversion(row.get("total_price")) for row in records]
        return round(sum(prices), 2)
    except Exception as e:
        print(f"Error calculating today total: {str(e)}")
        return 0.0


def get_last_expenses(limit=10):
    """
    Get the last several expenses from the current month's table.
    Returns a list of dictionaries with expense details.
    """
    try:
        table_name = f"items_{datetime.now().strftime('%Y_%m')}"
        table = get_table(BASE_ID, table_name)
        if not table:
            print(f"No table found for this month: {table_name}")
            return []
        
        table_id = table["id"]
        
        # Get total count to determine proper ordering
        count = get_table_record_count(table_id)
        
        url = f"{NOCODB_API_URL}/api/v2/tables/{table_id}/records"
        params = {
            "fields": "uuid,name,total_price,date,quantity,unit_price",
            "sort": "-date",  # Sort by date descending (newest first)
            "limit": limit,
            "offset": 0
        }
        
        resp = requests.get(url, headers=headers, params=params)
        
        if resp.status_code != 200:
            print(f"Failed to get records: {resp.status_code} {resp.text}")
            return []
            
        data = resp.json()
        records = data["list"] if "list" in data else data
        
        # Format the response similar to your ExpenseDate structure
        last_expenses = []
        for record in records:
            expense = {
                "id": record.get("uuid", ""),
                "amount": safe_float_conversion(record.get("total_price")),
                "name": record.get("name", ""),
                "date": record.get("date", ""),
            }
            last_expenses.append(expense)
        
        return last_expenses
        
    except Exception as e:
        print(f"Error getting last expenses: {str(e)}")
        return []

def fetch_and_store_monthly_data():
    global monthly_data
    table_name = f"items_{datetime.now().strftime('%Y_%m')}"
    table = get_table(BASE_ID, table_name)
    if not table:
        monthly_data = []
        return
    table_id = table["id"]
    # Get the count of records in the table to set the limit for fetching
    count = get_table_record_count(table_id)
    url = f"{NOCODB_API_URL}/api/v2/tables/{table_id}/records"
    params = {
        "fields": "name,quantity,total_price,date",
        "limit": count,
        "offset": 0
    }
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        monthly_data = []
        return
    data = resp.json()
    records = data["list"] if "list" in data else data
    monthly_data = records
    with open("monthly_data.json", "w") as f:
        json.dump(records, f, indent=2)


def monitor_and_update_data(interval=10):
    global data_needs_update
    last_count = 0
    while True:
        if data_needs_update:
            fetch_and_store_monthly_data()
            data_needs_update = False
            # Update last_count after fetching
            table_name = f"items_{datetime.now().strftime('%Y_%m')}"
            table = get_table(BASE_ID, table_name)
            if table:
                table_id = table["id"]
                count_url = f"{NOCODB_API_URL}/api/v2/tables/{table_id}/records/count"
                count_resp = requests.get(count_url, headers=headers)
                if count_resp.status_code == 200:
                    last_count = count_resp.json().get("count", 0)
        else:
            # Passive check for new data (optional)
            table_name = f"items_{datetime.now().strftime('%Y_%m')}"
            table = get_table(BASE_ID, table_name)
            if table:
                table_id = table["id"]
                count_url = f"{NOCODB_API_URL}/api/v2/tables/{table_id}/records/count"
                count_resp = requests.get(count_url, headers=headers)
                if count_resp.status_code == 200:
                    count = count_resp.json().get("count", 0)
                    if count != last_count:
                        data_needs_update = True
        time.sleep(interval)


def start_data_monitor_thread():
    global data_thread
    if data_thread is None or not data_thread.is_alive():
        data_thread = threading.Thread(target=monitor_and_update_data, daemon=True)
        data_thread.start()

# Returns the current month's data from memory.
# This function can be called to get the latest data without fetching from NocoDB again.
# It will return the data stored in the `monthly_data` variable, which is updated by the monitoring thread.
def get_monthly_data():
    """
    Returns the current month's data from memory.
    """
    global monthly_data
    return monthly_data if monthly_data else []


if __name__ == "__main__":
    # Example item (you can use your real parsed data here)
    item = {
        "unique_id": str(uuid.uuid4()),  # Generate a unique ID for the item
        "name": "Milk",
        "quantity": 2,
        "unit_price": 1.5,
        "date": "2024-06-18 12:30",
        "total_price": 3.0
    }
    # Generate table name as items_YYYY_MM
    table_name = f"items_{datetime.now().strftime('%Y_%m')}"

    table = get_table(BASE_ID, table_name)
    if table:
        print(f"Table already exists: {table_name}")
        table_id = table["id"]
    else:
        new_table = create_table(BASE_ID, table_name)
        if not new_table:
            exit("Table creation failed. Exiting.")
        table_id = new_table["id"]
    # Store the item in the table using dumy data above
    # add_row_to_table(table_id, item)

    # prices = get_week_total_price_list(table)
    # print("All total_prices for current week:", prices)
    # print("Sum for week:", sum(prices))
    # get_month_total_price()
    print("Total price for current month:", get_month_total_price())
    print("Total price for current week:", get_week_total_price_list(table_id))


