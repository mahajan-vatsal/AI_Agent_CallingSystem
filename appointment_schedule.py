import os
from dotenv import load_dotenv
from openai import OpenAI
from calendar_utils import create_event, get_slot_datetime, is_valid_appointment, is_slot_available, cancel_event, find_upcoming_appointment_by_email, is_email_already_booked
from email_utils import send_email
from speech_utils import transcribe_audio, text_to_speech
from datetime import datetime
import re

EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

load_dotenv()

client = OpenAI(api_key=os.getenv("FIREWORKS_API_KEY"), base_url="https://api.fireworks.ai/inference/v1")

MAX_RETRIES = 3

async def get_llm_response(prompt):
    try:
        response = client.chat.completions.create(
            model="accounts/fireworks/models/deepseek-v3",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("LLM error:", e)
        return "Sorry, I'm having trouble responding right now."

async def handle_patient_reply(audio_path):
    tries = 0
    while tries < MAX_RETRIES:
        transcript = transcribe_audio(audio_path)
        print("Patient said:", transcript)

        if not transcript.strip():
            tries += 1
            yield None, None, None, None, text_to_speech("I didn't hear anything clearly. Could you please repeat your appointment request?")
            continue

        prompt_info = f"""
You are a smart AI assistant for a doctor's clinic.
A patient said: "{transcript}"
Extract the intent (schedule/reschedule/cancel), date (in YYYY-MM-DD) The year always be the current year like this year 2025(make sense), and time (24-hour HH:MM).
Return only in this format:
Intent: schedule
Date: 2025-04-29
Time: 10:00
If any detail is unclear or missing, say: "I didn’t catch the full details. Could you please repeat?"
"""
        info_response = await get_llm_response(prompt_info)
        print("LLM Info Response:\n", info_response)

        if "I didn’t catch" in info_response:
            tries += 1
            yield None, None, None, None, text_to_speech("Sorry, I didn't catch all the details. Could you please repeat your appointment request clearly?")
            continue

        try:
            intent = next(line for line in info_response.splitlines() if "Intent:" in line).split(":", 1)[1].strip().lower()
            date = next(line for line in info_response.splitlines() if "Date:" in line).split(":", 1)[1].strip()
            time = next(line for line in info_response.splitlines() if "Time:" in line).split(":", 1)[1].strip()
        except Exception:
            tries += 1
            yield None, None, None, None, text_to_speech("There was an error understanding your appointment request. Could you please repeat?")
            continue

        if intent == "schedule":
            is_valid, reason = is_valid_appointment(date, time)
            if not is_valid:
                if reason == "Sunday":
                    invalid_prompt = f"""
A patient requested an appointment on {date}, which is a Sunday.
Inform the patient that the clinic is closed on Sundays.
Politely ask them to choose another day between Monday and Saturday.
"""
                elif reason == "Lunch Break":
                    invalid_prompt = f"""
A patient requested an appointment at {time} on {date}, which is during the doctor's lunch break (2pm to 4pm).
Inform them that the doctor is unavailable at this time.
Suggest they pick a time between 10am–2pm or 4pm–7pm.
"""
                else:
                    invalid_prompt = f"""
A patient requested a time of {time} on {date}, which is outside the clinic’s working hours (10am–2pm and 4pm–7pm).
Kindly inform them and ask for a new preferred time within working hours.
"""
                speak_invalid = await get_llm_response(invalid_prompt)
                yield None, None, None, None, text_to_speech(speak_invalid)
                tries += 1
                continue

            if not is_slot_available(date, time):
                unavailable_prompt = f"""
The requested slot {date} at {time} is already taken.
Politely ask the patient to suggest another date and time.
"""
                unavailable_response = await get_llm_response(unavailable_prompt)
                yield None, None, None, None, text_to_speech(unavailable_response)
                tries += 1
                continue

            ask_email_prompt = """
Now ask the patient to say their email address, spelling it letter by letter for clarity.
Tell them to speak clearly and slowly.
"""
            ask_email_text = await get_llm_response(ask_email_prompt)
            yield intent, transcript, date, time, text_to_speech(ask_email_text)
            return

        elif intent == "reschedule":
            yield intent, transcript, date, time, text_to_speech("Rescheduling functionality is not implemented yet. Please try again later.")
            return

        elif intent == "cancel":
            ask_email_prompt = """
Now ask the patient to say their email address, spelling it letter by letter for clarity.
Tell them to speak clearly and slowly.
"""
            ask_email_text = await get_llm_response(ask_email_prompt)
            yield intent, transcript, date, time, text_to_speech(ask_email_text)
            return

        else:
            tries += 1
            yield None, None, None, None, text_to_speech("Sorry, I didn't understand your request. Could you please repeat?")
    yield None, None, None, None, text_to_speech("Sorry, we couldn't understand your request. Please try calling again later.")


async def handle_email_spelling(audio_path):
    tries = 0
    while tries < MAX_RETRIES:
        spelled_email = transcribe_audio(audio_path)
        print("Spelled email (raw):", spelled_email)

        if not spelled_email.strip():
            tries += 1
            yield text_to_speech("I didn't catch your spelling. Please spell your email address again, slowly.")
            continue

        confirm_prompt = f"""
You are an AI assistant confirming an email address.
The patient said: "{spelled_email}". Try to reconstruct the email address.
Only output the email address.
"""
        email = await get_llm_response(confirm_prompt)
        print("Reconstructed Email:", email)

        confirmation_prompt = f"Did you say {email}? Please say yes or no."
        yield email, text_to_speech(confirmation_prompt)
        return

    yield None, text_to_speech("Sorry, we couldn't capture your email correctly. Please try calling again later.")

async def confirm_email_and_book(audio_path, date, time, email, service, calendar_id):
    tries = 0
    while tries < MAX_RETRIES:
        confirmation_reply = transcribe_audio(audio_path).lower()
        print("Patient confirmed:", confirmation_reply)

        if not confirmation_reply.strip():
            tries += 1
            yield text_to_speech("I didn't catch your response. Please say Yes or No.")
            continue

        if "yes" in confirmation_reply:
            if not is_email_already_booked(service, calendar_id, email):
                yield "email_already_used", text_to_speech("You already have an appointment booked with this email. Only one is allowed.")
                return


            if not is_slot_available(date, time):
                suggest_prompt = f"""
The slot on {date} at {time} is already booked.
Suggest three alternative slots between 10am–2pm or 4pm–7pm, Monday to Saturday.
Format:
1. YYYY-MM-DD at HH:MM
2. YYYY-MM-DD at HH:MM
3. YYYY-MM-DD at HH:MM
"""
                suggestions = await get_llm_response(suggest_prompt)

                speak_prompt = f"""
The appointment slot is not available.
Here are some alternative slots:
{suggestions}
Please say which one you prefer.
"""
                yield text_to_speech(await get_llm_response(speak_prompt))
                return

            start, end = get_slot_datetime(date, time)
            event = create_event(start, end, "Doctor Appointment", email)
            event_link = event.get("htmlLink") if event else "Unavailable"

            patient_email_body = await get_llm_response(f"""
Write a polite confirmation email for a patient for {date} at {time}.
Include event link: {event_link}.
Sign off "Thank you! - Dr. Mahajan, M.B.B.S"
Don't include patient's name
For example: 

Your appointment has been successfully scheduled on [Date] at [Time].
Please arrive 10 minutes early for formalities.
You can add the appointment to your calendar using the link below: [event_link]
Doctor: Dr. Vatsal Mahajan
Location: [Clinic Address]
Thank you!
— Team HealthCare
""")
            doctor_email_body = await get_llm_response(f"""
Inform the doctor of a booked appointment on {date} at {time}.
You can add the appointment to your calendar using the link below: {event_link}.

Thank you!
— Our AI Team.
""")

            send_email(email, "Your Appointment is Confirmed", patient_email_body)
            send_email("vatsalmahajan0007@gmail.com", "New Appointment Booked", doctor_email_body)

            final_confirm = await get_llm_response(f"Confirm to the patient their booking on {date} at {time} is complete and email sent.")
            yield "booked", text_to_speech(final_confirm)
            return

        elif "no" in confirmation_reply:
            repeat_email_prompt = """
Apologize and ask the patient to slowly spell their email address again.
"""
            yield "repeat_email", text_to_speech(await get_llm_response(repeat_email_prompt))
            return

        else:
            tries += 1
            yield None, text_to_speech("Sorry, I didn't understand. Please say Yes or No.")

    yield text_to_speech("Sorry, we couldn't confirm your appointment. Please try again later.")

# Handles appointment cancellation
async def handle_cancel_flow(email_audio_path, confirm_audio_path):
    # Step 1: Transcribe and reconstruct email
    spelled_email = transcribe_audio(email_audio_path)
    print("🔤 Raw spelled email from audio:", spelled_email)

    confirm_prompt = f"""
You are an AI assistant confirming an email address.
The patient said: "{spelled_email}". Try to reconstruct the email address.
Only output the email address.
"""
    email = (await get_llm_response(confirm_prompt)).strip()
    print("📧 Reconstructed Email:", email)

    # Step 1.5: Validate email format
    if not re.match(EMAIL_REGEX, email):
        print("❌ Invalid email format. Asking for re-spelling.")
        yield "repeat_email", None, None
        return

    # Step 2: Confirm reconstructed email using patient's Yes/No voice
    confirmation_text = transcribe_audio(confirm_audio_path)
    print("🗣️ Patient response to email confirmation:", confirmation_text)

    yes_no_prompt = f"""
You are a smart assistant. The patient responded: "{confirmation_text}".
Did the patient confirm the email (yes or no)? Output only "yes" or "no".
"""
    confirmed = (await get_llm_response(yes_no_prompt)).strip().lower()
    print("✅ Email confirmation result:", confirmed)

    if "no" in confirmed:
        yield "repeat_email", None, None
        return

    # Step 3: Proceed to cancel appointment
    appointment = find_upcoming_appointment_by_email(email)
    if not appointment:
        not_found_prompt = f"""
You are a voice assistant. No upcoming appointment was found for {email}.
Politely inform the patient and suggest they double-check the email or book a new appointment if needed.
"""
        speak_text = await get_llm_response(not_found_prompt)
        print(f"🔍 No appointment found for: {email}")
        yield "not_found", email, text_to_speech(speak_text)
        return

    event_id = appointment['id']
    event_start = appointment['start'].get('dateTime', '')
    event_datetime = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
    date_str = event_datetime.strftime('%Y-%m-%d')
    time_str = event_datetime.strftime('%H:%M')

    if cancel_event(event_id):
        # Send cancellation emails
        cancel_patient_email = f"""
You are an email assistant. Write a polite email to the patient at {email}, confirming that their appointment on {date_str} at {time_str} has been successfully canceled.
Sign off with "Thank you!"
"""
        cancel_doctor_email = f"""
Notify the doctor that the appointment with a patient (email: {email}) on {date_str} at {time_str} has been canceled.
Use a professional tone. Sign off with "Regards".
"""
        patient_body = await get_llm_response(cancel_patient_email)
        doctor_body = await get_llm_response(cancel_doctor_email)

        send_email(email, "Your Appointment has been Canceled", patient_body)
        send_email("vatsalmahajan0007@gmail.com", "Appointment Canceled", doctor_body)

        # Speak cancellation confirmation
        cancel_confirm_prompt = f"""
You are a voice assistant. Inform the patient that their appointment on {date_str} at {time_str} has been canceled and a cancellation email has been sent.
End with a polite thank-you message.
"""
        cancel_confirm_text = await get_llm_response(cancel_confirm_prompt)
        print(f"📨 Appointment canceled and emails sent for: {email}")
        yield "canceled", email, text_to_speech(cancel_confirm_text)
    else:
        error_prompt = f"""
You are a voice assistant. Inform the patient that there was an error canceling their appointment.
Kindly ask them to try again or contact the clinic directly.
"""
        print(f"❗ Error canceling event for: {email}")
        yield "error", email, text_to_speech(await get_llm_response(error_prompt))





#Wait... 
#While reviewing the flow of appointment_schedule.py, I got some glitches, which I'm mentioning here and hoping for your help to solve them:

#1. What if LLM say, 'I didn't understand your request. Could you please repeat?' In that case, what happens? I think we need to call the function handle_patient_reply, and again, the voice will pass through it, and the loops will continue till we get clear audio from the patient.
#2. What if is_slot_available and the slot is not available, so in this case, LLM ask the patient to speak the preferred data and time, then we need to extract that preferred data and time from the new audio file, and again pass through is_slot_available. The loops will continue till we get an available slot from the patient side.
#3. What if the patient says 'No' for the confirmation reply? In this case, I think we have to ask the patient to repeat the email and then pass it through handle_email_spelling. The loops will continue till we get a 'Yes' for the confirmation reply from the patient side.
#4. What did the patient don't respond to the confirmation for Yes or No? In that case, the model or agent should need to ask again for the confirmation and then pass that audio through confirmation_email_and_book. 

#I hope you understand what I want to ask, as this makes the flow seamless. Now, make changes in the appointment_schedule.py file or send me the whole new code. but let me know where you are making the changes from the previous version of the file.