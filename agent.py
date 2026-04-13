from groq import Groq
from groq import RateLimitError
from config import GROQ_API_KEY
from tools import get_menu_from_sheet, restaurant_tools, execute_tool_call
import json

MAX_HISTORY = 10
MAX_TOOL_CALLS = 3
client = Groq(api_key=GROQ_API_KEY)

class WhatsAppAgent:
    def __init__(self):
        self.system_instruction = (
            "You are a polite, helpful AI assistant for a restaurant.\n"
            "Your job is to help customers view the menu, place orders, modify or cancel existing orders.\n"
            "Be conversational and concise.\n\n"

            "STRICT RULES — follow these exactly:\n"
            "1. When a user wants to place an order, collect ALL of the following before doing anything else:\n"
            "   - Their full name\n"
            "   - Their phone number\n"
            "   - Their delivery address\n"
            "   - The items they want (must exist on the menu)\n"
            "2. Once you have all details, summarize the order clearly with the total price and ask: 'Shall I confirm this order?'\n"
            "3. ONLY call add_new_order after the customer explicitly says YES or confirms.\n"
            "4. NEVER call add_new_order more than once per confirmation.\n"
            "5. If the user asks for the menu, show it clearly from the menu data below.\n"
            "6. If the user wants to cancel or update, call get_customer_orders first, show them their orders, then ask which one.\n"
            "7. Do not ask for info you already have in the conversation.\n\n"

            f"Current menu:\n{get_menu_from_sheet()}"
        )
        self.conversations = {}  # {phone: [messages]}

    def handle_message(self, user_phone: str, message_text: str) -> str:
        try:
            if user_phone not in self.conversations:
                self.conversations[user_phone] = []

            history = self.conversations[user_phone]
            history.append({"role": "user", "content": message_text})

            tool_call_count = 0

            while True:
                context = history[-MAX_HISTORY:]

                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": self.system_instruction},
                        *context
                    ],
                    tools=restaurant_tools,
                    tool_choice="auto" if tool_call_count < MAX_TOOL_CALLS else "none",
                    temperature=0.0,
                    max_tokens=512,
                )

                message = response.choices[0].message

                if not message.tool_calls:
                    reply = message.content or "Sorry, I didn't understand that. Could you rephrase?"
                    history.append({"role": "assistant", "content": reply})
                    return reply

                tool_call_count += 1

                history.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}

                    print(f"[TOOL CALL] {tool_name}({tool_args})")
                    tool_result = execute_tool_call(tool_name, tool_args)
                    print(f"[TOOL RESULT] {tool_result}")

                    history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result,
                    })

        except RateLimitError:
            return "We're a bit busy right now! Please try again in a few minutes. 🙏"
        except Exception as e:
            print(f"[ERROR] {e}")
            return "Something went wrong on our end. Please try again!"