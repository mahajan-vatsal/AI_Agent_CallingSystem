import openai
import os
from dotenv import load_dotenv
from calendar_utils import create_event, get_slot_datetime
from email_utils import send_email

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Simulated parsed data (you'll get these from transcribed speech + LLM parsing)
SIMULATED_EMAIL = "patient@example.com"
SIMULATED_DATE = "2025-04-25"
SIMULATED_TIME = "10:40"
SIMULATED_SUMMARY = "Checkup with Dr. Mahajan"

async def process_call_logic(data):
    # 1. Greet user
    greeting_prompt = """
You are a friendly assistant at a doctor's clinic.
Greet the patient and ask if they want to schedule, reschedule, or cancel an appointment.
Keep it short and professional.
"""
    llm_response = await get_llm_response(greeting_prompt)

    # 2. Simulate a scenario where user chooses to schedule
    # You'll replace this with logic to extract intent, email, date, and time
    start, end = get_slot_datetime(SIMULATED_DATE, SIMULATED_TIME)

    try:
        event = create_event(start, end, SIMULATED_SUMMARY, SIMULATED_EMAIL)
        calendar_link = event.get("htmlLink", "No link available")
        
        # 3. Send confirmation email
        subject = "Appointment Confirmation with Dr. Mahajan"
        body = f"""Dear Patient,

Your appointment has been scheduled for {SIMULATED_DATE} at {SIMULATED_TIME} with Dr. Mahajan.
Location: Clinic Address
Google Calendar Link: {calendar_link}

Please arrive 10 minutes early.

Best regards,
Clinic AI Assistant
"""
        send_email(SIMULATED_EMAIL, subject, body)

        confirmation_message = f"{llm_response} Your appointment is confirmed for {SIMULATED_DATE} at {SIMULATED_TIME}."

    except Exception as e:
        print("Error during appointment scheduling or email:", e)
        confirmation_message = "Sorry, there was an issue scheduling your appointment."

    # 4. Respond to caller
    return f"""
    <Response>
        <Say>{confirmation_message}</Say>
        <Record timeout="5" maxDuration="60" />
    </Response>
    """

async def get_llm_response(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.6
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("LLM error:", e)
        return "Sorry, I'm having trouble responding right now."
