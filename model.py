from pydantic import BaseModel
from typing import Dict, List, Any, Optional

class OrderCreate(BaseModel):
    customer_name: str
    customer_phone: str
    delivery_address: str
    items: List[Dict[str, Any]]
    total_price: float

class OrderUpdate(BaseModel):
    # Everything is Optional so you can update just one field (like status) or multiple
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    delivery_address: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None
    total_price: Optional[float] = None
    status: Optional[str] = None