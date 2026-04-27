# tools.py
import json
from database import get_db_connection, redis_client
from config import REFRESH_MENU_PERIOD
from psycopg2.extras import RealDictCursor




def get_menu() -> str:
    cached_menu = redis_client.get("restaurant_menu")
    if cached_menu:
        return cached_menu

    print("[SYSTEM] Fetching menu from PostgreSQL...")
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT item_name, price FROM menu WHERE available = TRUE;")
            records = cursor.fetchall()
            
            if not records:
                return "The menu is currently empty."

            compressed_menu = "Menu:\n"
            for item in records:
                compressed_menu += f"- {item['item_name']}: {item['price']}EGP\n"
                
            redis_client.setex("restaurant_menu", REFRESH_MENU_PERIOD, compressed_menu)
            return compressed_menu
    except Exception as e:
        return f"Error fetching menu: {e}"
    finally:
        conn.close()

def get_customer_orders(phone: str) -> str:
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, items, status 
                FROM orders 
                WHERE customer_phone = %s;
            """, (phone,))
            records = cursor.fetchall()

            if not records:
                return "No orders found."
            
            compressed_orders = "Orders:\n"
            for o in records:
                # Assuming items is stored as a JSON string or JSONB array
                compressed_orders += f"ID:{o['id']} | Stat:{o['status']} | Items:{o['items']}\n"
            return compressed_orders
    except Exception as e:
        return f"Error fetching orders: {e}"
    finally:
        conn.close()

def add_new_order(phone: str, name: str, items: str, address: str) -> str:
    conn = get_db_connection()
    try:
        # In a real app, you would parse the 'items' string and calculate total_price here.
        # For simplicity, we are saving it directly as a flat string and setting total_price to 0.0
        # If you want to use the Pydantic OrderCreate model, you must parse the LLM's 'items' string into a List[OrderItem] first.
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO orders (customer_name, customer_phone, delivery_address, items, total_price, status)
                VALUES (%s, %s, %s, %s, %s, 'Pending')
                RETURNING id;
            """, (name, phone, address, json.dumps([{"order_text": items}]), 0.0))
            
            new_id = cursor.fetchone()[0]
            conn.commit()
            return f"Success! Order #{new_id} has been created."
    except Exception as e:
        conn.rollback()
        return f"DB Error: {e}"
    finally:
        conn.close()

def cancel_order(order_id: str) -> str:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE orders 
                SET status = 'Cancelled' 
                WHERE id = %s AND status = 'Pending'
                RETURNING id;
            """, (order_id,))
            
            updated_row = cursor.fetchone()
            conn.commit()
            
            if updated_row:
                return f"Order #{order_id} has been successfully cancelled."
            else:
                return f"Sorry, order #{order_id} cannot be cancelled (it may not exist or is no longer Pending)."
    except Exception as e:
        conn.rollback()
        return f"Error: {e}"
    finally:
        conn.close()

def update_order(order_id: str, new_items: str = None, new_address: str = None) -> str:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # First, check if it's pending
            cursor.execute("SELECT status FROM orders WHERE id = %s;", (order_id,))
            row = cursor.fetchone()
            
            if not row:
                return f"No order found with ID #{order_id}."
            if row[0] != 'Pending':
                return f"Sorry, order #{order_id} cannot be updated as it is already {row[0]}."

            # Apply updates
            if new_items and new_address:
                cursor.execute("UPDATE orders SET items = %s, delivery_address = %s WHERE id = %s;", (json.dumps([{"order_text": new_items}]), new_address, order_id))
            elif new_items:
                cursor.execute("UPDATE orders SET items = %s WHERE id = %s;", (json.dumps([{"order_text": new_items}]), order_id))
            elif new_address:
                cursor.execute("UPDATE orders SET delivery_address = %s WHERE id = %s;", (new_address, order_id))
            else:
                return "No changes provided."

            conn.commit()
            return f"Order #{order_id} has been updated successfully."
    except Exception as e:
        conn.rollback()
        return f"Error updating order: {e}"
    finally:
        conn.close()

TOOL_MAP = {
    "get_menu":            get_menu,  
    "get_customer_orders": get_customer_orders,
    "add_new_order":       add_new_order,
    "cancel_order":        cancel_order,
    "update_order":        update_order,
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
            "name": "get_menu",
            "description": "Fetch the restaurant menu. Call this when the user asks for the menu OR to verify item names and prices before calculating the order total.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
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
            "name": "update_order",
            "description": "Updates the details of a pending order by its order ID. Call get_customer_orders first to get the order ID.",
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