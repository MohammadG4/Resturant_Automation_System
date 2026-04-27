from pyexpat import model

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware 
import requests
from config import WHATSAPP_TOKEN, PHONE_NUMBER_ID,VERIFY_TOKEN,ORIGINS_LIST
from agent import WhatsAppAgent
from utils import get_all_orders, get_orders_by_phone, get_order_by_id, add_order, update_order_by_id, get_menu, add_menu, update_menu, delete_menu_by_id
from model import OrderCreate, OrderUpdate, MenuCreate, MenuUpdate

app = FastAPI(title="AI Restaurant Agent")
agent = WhatsAppAgent()

origins = ORIGINS_LIST
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, PATCH, etc.)
    allow_headers=["*"], # Allows all headers
)

# Make sure this exactly matches what you type in the Meta Dashboard!
# VERIFY_TOKEN = "verify_for_me_tklsfofo" 

# In-memory session store 

sessions = {}

async def send_whatsapp_message(to_number: str, text: str):
    """Helper function to send responses via WhatsApp API."""
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text}
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"Failed to send message: {response.text}")

@app.get("/")
async def root():
    return {"message": "Welcome to the AI Restaurant Agent! Send a message to our WhatsApp number to place an order."}

# --- ADD THIS BLOCK FOR META VERIFICATION ---
@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("WEBHOOK_VERIFIED")
            return Response(content=challenge, status_code=200)
        else:
            return Response(status_code=403)
            
    return Response(status_code=400)
# --------------------------------------------


processed_message_ids = set() 

@app.post("/webhook")
async def receive_whatsapp_message(request: Request):
    data = await request.json()

    try:
        value = data["entry"][0]["changes"][0]["value"]
        
        if "messages" not in value:
            return {"status": "ok"}

        message = value["messages"][0]
        message_id = message["id"]  

        # ← Ignore if already processed
        if message_id in processed_message_ids:
            return {"status": "ok"}
        processed_message_ids.add(message_id)

        user_phone = message["from"]
        user_text = message["text"]["body"]

        ai_response = agent.handle_message(user_phone, user_text)
        await send_whatsapp_message(user_phone, ai_response)

    except (KeyError, IndexError):
        pass

    return {"status": "ok"}
@app.get("/orders")
async def get_orders():
    orders = get_all_orders()
    return {"orders": orders}

@app.get("/orders/{phone}")
async def get_orders_by_customer(phone: str):
    orders = get_orders_by_phone(phone)
    if not orders:
        raise HTTPException(status_code=404, detail="No orders found for this phone number.")
    return {"orders": orders}

@app.get("/order/{id}")
async def fetch_order_by_id(id: int): # Renamed function to avoid conflict with imported DB function
    order = get_order_by_id(id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    return {"order": order}

@app.post("/order")
async def create_new_order(order: OrderCreate):
    # Extract validated data from Pydantic model and pass to the DB function
    new_order = add_order(
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        delivery_address=order.delivery_address,
        items=order.items,
        total_price=order.total_price
    )
    if not new_order:
        raise HTTPException(status_code=500, detail="Failed to create order.")
    return {"order": new_order}

@app.patch("/order/{order_id}")
async def update_existing_order(order_id: int, order_update: OrderUpdate):
    # .model_dump(exclude_unset=True) ensures we only grab fields the user actually sent
    update_data = order_update.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided to update.")

    # Call the dynamic update function we built earlier
    success = update_order_by_id(order_id, update_data)
    
    if not success:
        raise HTTPException(status_code=404, detail="Order not found or update failed.")
        
    return {
        "message": f"Order {order_id} updated successfully.", 
        "updated_fields": update_data
    }

@app.get("/menu")
async def fetch_menu():
    """Fetch the entire menu."""
    menu_items = get_menu()
    return {"menu": menu_items}

@app.post("/menu")
async def create_new_menu_item(item: MenuCreate):
    """Add a new item to the menu."""
    new_item = add_menu(
        item_name=item.item_name,
        price=item.price,
        available=item.available
    )
    if not new_item:
        raise HTTPException(status_code=500, detail="Failed to add menu item.")
    return {"item": new_item}

@app.patch("/menu/{item_id}")
async def update_existing_menu_item(item_id: int, item_update: MenuUpdate):
    """Update an existing menu item (e.g., change price or availability)."""
    # Exclude fields that were not explicitly set in the request
    update_data = item_update.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided to update.")

    # Call the dynamic update function
    success = update_menu(item_id, update_data)
    
    if not success:
        raise HTTPException(status_code=404, detail="Menu item not found or update failed.")
        
    return {
        "message": f"Menu item {item_id} updated successfully.", 
        "updated_fields": update_data
    }

@app.delete("/menu/{item_id}")
async def remove_menu_item(item_id: int):
    """Delete a menu item by its ID."""
    success = delete_menu_by_id(item_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Menu item not found or could not be deleted.")
        
    return {"message": f"Menu item {item_id} deleted successfully."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)