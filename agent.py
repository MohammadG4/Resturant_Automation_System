import json
import redis
from groq import Groq, RateLimitError
from config import GROQ_API_KEY, MAX_HISTORY, MAX_TOOL_CALLS, SESSION_TIMEOUT_SECONDS
from tools import restaurant_tools,execute_tool_call, get_menu_from_sheet
from database import redis_client

# Initialize Redis Connection
client = Groq(api_key=GROQ_API_KEY)

class WhatsAppAgent:

    def _get_system_instruction(self,whatsapp_number):
        return (
    "Role & Persona\n"
    "You are a polite, helpful AI assistant for a restaurant. Your job is to help customers view the menu, place orders, and modify or cancel existing orders.\n"
    "Language & Tone: You must communicate EXCLUSIVELY in Professional Egyptian Arabic (العامية المصرية المهذبة).\n"
    "Professionalism: Always use respectful terms of address such as 'حضرتك' or 'يا فندم'. STRICTLY AVOID street slang, overly casual words, or overly familiar terms (e.g., never use 'يسطا', 'يا صاحبي', etc.).\n"
    "Style: Be conversational, warm, and concise.\n\n"

    " [CRITICAL SYSTEM INFO & PHONE NUMBERS] \n"
            f"The user's verified WhatsApp Account Number is: {whatsapp_number}\n"
            "Here is how you handle phone numbers:\n"
            "1. DEFAULT: Always assume the delivery contact number is the WhatsApp Account Number.\n"
            "2. EXCEPTION: If the customer EXPLICITLY provides a different phone number for the order, use their provided number for the `add_new_order` tool.\n"
            "3. ORDER HISTORY: When calling `get_customer_orders`, default to checking the WhatsApp Account Number, but if the user asks to check orders for a different number they previously used, use that one.\n"
            "DO NOT ask the user for their phone number upfront, only confirm it if they mention delivering to someone else.\n\n"
    "STRICT RULES — Follow these exactly:\n"
    "1. The Greeting: Always greet the customer first and welcome them to the restaurant (e.g., 'أهلاً بحضرتك يا فندم في مطعمنا، أقدر أساعدك إزاي النهاردة؟').\n"
    "2. Viewing the Menu: You DO NOT have the menu memorized. ONLY call the `get_menu` tool if the user EXPLICITLY asks for the menu, asks what food you have, or asks for prices. DO NOT call it for basic greetings like 'Hello' or 'السلام عليكم'.\n"
    "3. Order Collection: When a user wants to place an order, you must collect ALL of the following details:\n"
    "   - Their full name\n"
    "   - Their delivery address\n"
    "   - The specific items they want (must exist on the retrieved menu)\n"
    "   CRITICAL: Before summarizing the order and asking for confirmation, make sure all items exist and accurately calculate the total price and dont add the order before asking for confirmation and they confirm.\n"
    "   (Note: Do not ask for their phone number since the system already tracks it via WhatsApp, but ensure you include it when calling the order tool).\n"
    "4. Memory: Do not ask the user for information they have already provided in the conversation.\n"
    "5. Order Summary & Confirmation: Once you have all details, summarize the order clearly, calculate the total price, and explicitly ask for confirmation (e.g., 'إجمالي الحساب كذا.. تحب حضرتك أأكد الطلب؟').\n"
    "6. Unconfirmed Orders: If the user is just chatting or hasn't explicitly confirmed, reply with normal conversational text in professional Egyptian Arabic.\n"
    "7. Confirmed Orders (TOOL CALL): ONLY when the customer explicitly says YES to the final summary, you must call the `add_new_order` tool to save the order. DO NOT output raw JSON in your text response.\n"
    "8. NEVER call `add_new_order` more than once per confirmation.\n"
    "9. Modifying/Canceling: If the user wants to cancel or update, call the `get_customer_orders` tool first, show them their orders, then ask which one they want to modify.\n\n"

    "Check your logic and tool parameters carefully before executing.\n\n"

    "TOOL CALLING CONSTRAINT:\n"
            "DO NOT write tool calls like <function=...> in your text response. ONLY use the native tool calling API.\n\n"

    )

    def _get_session(self, phone: str) -> list:
        session_data = redis_client.get(f"session:{phone}")
        if session_data:
            return json.loads(session_data)
        return []

    def _save_session(self, phone: str, history: list):
        trimmed_history = history[-MAX_HISTORY:]
        redis_client.setex(
            f"session:{phone}",
            SESSION_TIMEOUT_SECONDS,
            json.dumps(trimmed_history)
        )

    def handle_message(self, user_phone: str, message_text: str) -> str:

        lock_name = f"lock:{user_phone}"
        
        try:
            with redis_client.lock(lock_name, timeout=60, blocking_timeout=10):
                
                # 1. Fetch history from Redis
                history = self._get_session(user_phone)

                # 2. Append new user message
                history.append({"role": "user", "content": message_text})
                
                tool_call_count = 0

                while True:
                    if tool_call_count >= MAX_TOOL_CALLS:
                        error_msg = "بعتذر لحضرتك جداً، في مشكلة بسيطة في السيستم دلوقتي. ممكن نحاول نأكد الطلب تاني؟"
                        history.append({"role": "assistant", "content": error_msg})
                        self._save_session(user_phone, history)
                        return error_msg

                    # API Call to Groq
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "system", "content": self._get_system_instruction(user_phone)}] + history,
                        tools=restaurant_tools,
                        tool_choice="auto",
                        temperature=0.0,
                        max_tokens=512,
                    )
                    request_number = redis_client.incr("global_api_requests")
                    message = response.choices[0].message
                    if hasattr(response, 'usage') and response.usage:
                        self.current_usage = {
                            "request_number": request_number,
                            "prompt": response.usage.prompt_tokens,
                            "completion": response.usage.completion_tokens,
                            "total": response.usage.total_tokens
                        }
                    if not message.tool_calls:
                        reply = message.content or "عفواً، مفهمتش حضرتك، ممكن توضح أكتر؟"
                        history.append({"role": "assistant", "content": reply})
                        
                        # 3. SAVE TO REDIS before returning
                        self._save_session(user_phone, history)
                        return reply

                    tool_call_count += 1

                    history.append({
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": [tc.model_dump() for tc in message.tool_calls]
                    })

                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}

                        print(f"[TOOL CALL] {tool_name}({tool_args})")
                        tool_result = execute_tool_call(tool_name, tool_args)
                        print(f"[TOOL RESULT] {tool_result}")

                        if tool_name == "add_new_order" and "success" in str(tool_result).lower():
                            tool_result += "\n[SYSTEM STRICT DIRECTIVE: Order confirmed. Do NOT call add_new_order again for this session.]"

                        history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(tool_result),
                        })

        except redis.exceptions.LockError:
            # لو العميل فضل يبعت رسايل ورا بعض والسيستم مقفول عليه، هنرد عليه بالرسالة دي
            return "لحظة واحدة يا فندم، السيستم بيعالج رسالتك اللي فاتت..."
        except RateLimitError:
            return "السيستم عليه ضغط شوية يا فندم، ثواني ونجرب تاني! 🙏"
        except Exception as e:
            print(f"[ERROR] {e}")
            return "حصلت مشكلة تقنية، بعتذر لحضرتك. هنحلها فوراً!"