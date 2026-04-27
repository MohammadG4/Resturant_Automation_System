import json
from database import get_db_connection
from psycopg2.extras import RealDictCursor


def get_all_orders():
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id, customer_name,customer_phone,delivery_address, items, status, total_price, created_at FROM orders;")
            return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching all orders: {e}")
        return []
    finally:
        conn.close()

def get_orders_by_phone(phone: str):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id, customer_name,customer_phone,delivery_address, items, status, total_price,created_at FROM orders WHERE customer_phone = %s;", (phone,))
            return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching orders for phone {phone}: {e}")
        return []
    finally:
        conn.close()

def get_order_by_id(order_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id, customer_name,customer_phone,delivery_address, items, status, total_price,created_at FROM orders WHERE id = %s;", (order_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"Error fetching order with ID {order_id}: {e}")
        return None
    finally:
        conn.close()





def add_order(customer_name: str, customer_phone: str, delivery_address: str, items: list, total_price: float):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # We use json.dumps(items) to ensure the Python list/dict maps correctly to PostgreSQL JSONB
            cursor.execute(
                """
                INSERT INTO orders (customer_name, customer_phone, delivery_address, items, total_price) 
                VALUES (%s, %s, %s, %s, %s) RETURNING id, status, created_at;
                """,
                (customer_name, customer_phone, delivery_address, json.dumps(items), total_price)
            )
            new_order = cursor.fetchone()
            conn.commit()  # Save the transaction
            return new_order
    except Exception as e:
        conn.rollback()  # Rollback on error to prevent locks
        print(f"Error adding order: {e}")
        return None
    finally:
        conn.close()


def update_order_by_id(order_id: int, update_data: dict):
    """
    Dynamically updates an order based on the provided dictionary.
    Example usage: 
        update_order_by_id(1, {"status": "Confirmed"})
        update_order_by_id(2, {"items": new_items_list, "total_price": 250.00})
    """
    if not update_data:
        return False

    # Security: Ensure we only update valid columns from your schema
    valid_columns = {'customer_name', 'customer_phone', 'delivery_address', 'items', 'total_price', 'status'}
    
    set_clauses = []
    values = []

    for key, value in update_data.items():
        if key in valid_columns:
            set_clauses.append(f"{key} = %s")
            # If updating the items column, encode it back to JSON
            if key == 'items' and isinstance(value, (list, dict)):
                values.append(json.dumps(value))
            else:
                values.append(value)

    if not set_clauses:
        return False

    query = f"UPDATE orders SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"
    values.append(order_id)

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, tuple(values))
            updated_order = cursor.fetchone()
            conn.commit()
            
            # Returns True if the order existed and was updated, False otherwise
            return updated_order is not None
    except Exception as e:
        conn.rollback()
        print(f"Error updating order {order_id}: {e}")
        return False
    finally:
        conn.close()