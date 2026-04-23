from agent import WhatsAppAgent
import sys

def run_test_chat():
    print("="*50)
    print("🤖 جاري تشغيل النظام... (تأكد من تشغيل Redis Server)")
    print("="*50)

    try:
        # أخذ نسخة من الـ Agent
        agent = WhatsAppAgent()
        print("✅ النظام جاهز للعمل!")
    except Exception as e:
        print(f"❌ حصلت مشكلة أثناء تشغيل النظام: {e}")
        sys.exit(1)

    # تحديد رقم تليفون وهمي للتجربة
    test_phone = "+37289421832"
    print(f"📱 تم تعيين رقم هاتف تجريبي: {test_phone}")
    print("💡 اكتب 'exit' أو 'quit' للخروج من المحادثة.\n")
    print("="*50)

    # حلقة لا نهائية للمحادثة (CLI Chat Loop)
    while True:
        try:
            # 1. استقبال رسالة المستخدم من الـ Terminal
            user_input = input("\n[أنت 👨‍💻]: ")
            
            # إنهاء المحادثة لو المستخدم كتب exit
            if user_input.lower() in ['exit', 'quit']:
                print("👋 جاري إغلاق النظام. مع السلامة!")
                break
            
            # تجاهل الإدخال الفاضي
            if not user_input.strip():
                continue

            # 2. إرسال الرسالة للـ Agent واستقبال الرد
            print("⏳ الـ AI بيفكر...")
            response = agent.handle_message(test_phone, user_input)

            # 3. طباعة رد الـ AI
            print(f"\n[المساعد الآلي 🤖]:\n{response}")

            # =========== طباعة فاتورة التوكنز ===========
            if hasattr(agent, 'current_usage') and agent.current_usage:
                tokens = agent.current_usage
                print("\n" + "-"*40)
                print("📊 [Token Usage Report]")
                print(f"📊 [API Analytics] - Request #{tokens['request_number']}")
                print(f"📥 Input (Prompt):     {tokens['prompt']} tokens")
                print(f"📤 Output (Completion): {tokens['completion']} tokens")
                print(f"💰 Total Cost:         {tokens['total']} tokens")
                print("-" * 40)
            # ============================================

        except KeyboardInterrupt:
            # لو دوست Ctrl+C عشان تقفل السكريبت
            print("\n👋 تم إيقاف النظام (KeyboardInterrupt).")
            break
        except Exception as e:
            print(f"\n❌ خطأ غير متوقع: {e}")

if __name__ == "__main__":
    run_test_chat()