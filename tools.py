import json
import uuid
from database import orders_sheet, menu_sheet


def get_menu_from_sheet() -> str:
    records = menu_sheet.get_all_records()
    return json.dumps(records, ensure_ascii=False)

def get_customer_orders(phone: str) -> str:
    """Returns all orders for this phone number with their order IDs and status."""
    all_rows = orders_sheet.get_all_values()
    headers = all_rows[0] 
    
    customer_orders = []
    for row in all_rows[1:]:  # skip header
        if len(row) >= 6 and row[1] == phone:
            customer_orders.append({
                "order_id": row[0],
                "items":    row[3],
                "address":  row[4],
                "status":   row[5],
            })
    
    if not customer_orders:
        return "No orders found for this phone number."
    
    return json.dumps(customer_orders, ensure_ascii=False)

def add_new_order(phone: str, name: str, items: str, address: str) -> str:
    order_id = str(uuid.uuid4())[:8].upper()  # e.g. "A1B2C3D4"
    orders_sheet.append_row([order_id, phone, name, items, address, "Pending"])
    return f"Order successfully placed! Your order ID is: #{order_id}"

def cancel_order(order_id: str) -> str:
    all_rows = orders_sheet.get_all_values()
    for i, row in enumerate(all_rows[1:], start=2): 
        if row[0] == order_id:
            if row[5] == "Pending":
                orders_sheet.update_cell(i, 6, "Cancelled")
                return f"Order #{order_id} has been successfully cancelled."
            else:
                return f"Sorry, order #{order_id} cannot be cancelled as it is already {row[5]}."
    return f"No order found with ID #{order_id}."

def update_order_items(order_id: str, new_items: str) -> str:
    all_rows = orders_sheet.get_all_values()
    for i, row in enumerate(all_rows[1:], start=2):
        if row[0] == order_id:
            if row[5] == "Pending":
                orders_sheet.update_cell(i, 4, new_items)
                return f"Order #{order_id} has been updated to: {new_items}"
            else:
                return f"Sorry, order #{order_id} cannot be updated as it is already {row[5]}."
    return f"No order found with ID #{order_id}."



TOOL_MAP = {
    "get_customer_orders": get_customer_orders,
    "add_new_order":       add_new_order,
    "cancel_order":        cancel_order,
    "update_order_items":  update_order_items,
}

def execute_tool_call(tool_name: str, tool_args: dict) -> str:
    func = TOOL_MAP.get(tool_name)
    if func:
        return func(**(tool_args or {}))
    return f"Error: Unknown tool '{tool_name}'"



restaurant_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_customer_orders",
            "description": "Fetches all orders for a customer by their phone number. Call this first before cancelling or updating so the customer can choose which order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Customer's phone number"},
                },
                "required": ["phone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_new_order",
            "description": "Saves a new confirmed order. Only call after the customer has explicitly confirmed all details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone":   {"type": "string", "description": "Customer's phone number"},
                    "name":    {"type": "string", "description": "Customer's name"},
                    "items":   {"type": "string", "description": "Ordered items with quantities e.g. '2x Burger, 1x Fries'"},
                    "address": {"type": "string", "description": "Delivery address"},
                },
                "required": ["phone", "name", "items", "address"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_order",
            "description": "Cancels an order by its order ID. Call get_customer_orders first to get the order ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The order ID to cancel e.g. 'A1B2C3D4'"},
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_order_items",
            "description": "Updates the items of a pending order by its order ID. Call get_customer_orders first to get the order ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id":  {"type": "string", "description": "The order ID to update"},
                    "new_items": {"type": "string", "description": "The new items e.g. '1x Pizza, 2x Cola'"},
                },
                "required": ["order_id", "new_items"]
            }
        }
    },
]