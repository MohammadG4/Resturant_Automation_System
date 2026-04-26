from pydantic import BaseModel
from typing import List, Optional

# Define the structure for a single item in an order
class OrderItem(BaseModel):
    item_name: str
    price: float
    available: bool

# Define the structure for the complete order
class OrderCreate(BaseModel):
    order_id: str
    customer_name: str
    customer_phone: str
    delivery_address: Optional[str] = None
    items: List[OrderItem]
