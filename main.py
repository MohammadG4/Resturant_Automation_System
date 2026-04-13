from fastapi import FastAPI, Request, HTTPException
import requests
from config import WHATSAPP_TOKEN, PHONE_NUMBER_ID
from agent import WhatsAppAgent

app = FastAPI(title="AI Restaurant Agent")
agent = WhatsAppAgent()

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)