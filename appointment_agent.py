import os
from dotenv import load_dotenv
from openai import OpenAI
from calendar_utils import create_event, get_slot_datetime, is_valid_appointment, find_upcoming_appointment_by_email, cancel_event
from email_utils import send_email
from speech_utils import transcribe_audio, text_to_speech
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("FIREWORKS_API_KEY"), base_url="https://api.fireworks.ai/inference/v1")

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
    transcript = transcribe_audio(audio_path)
    print("Patient said:", transcript)

    prompt_info = f"""
You are a smart AI assistant for a doctor's clinic.
A patient said: "{transcript}"
Extract the intent (schedule/reschedule/cancel), date (in YYYY-MM-DD), and time (24-hour HH:MM).
Return only in this format:
Intent: schedule
Date: 2025-04-29
Time: 10:00
If any detail is unclear or missing, say: "I didn’t catch the full details. Could you please repeat?"
"""
    info_response = await get_llm_response(prompt_info)
    print("LLM Info Response:\n", info_response)

    if "I didn’t catch" in info_response:
        return transcript, text_to_speech("Sorry, I didn't catch all the details. Could you please repeat your appointment request clearly?")

    try:
        intent = next(line for line in info_response.splitlines() if "Intent:" in line).split(":", 1)[1].strip().lower()
        date = next(line for line in info_response.splitlines() if "Date:" in line).split(":", 1)[1].strip()
        time = next(line for line in info_response.splitlines() if "Time:" in line).split(":", 1)[1].strip()
    except Exception:
        return transcript, text_to_speech("There was an error extracting intent, date, or time. Please try again.")

    # 🔁 Route based on Intent
    if intent == "schedule":
        # Continue to schedule flow
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
Suggest they pick a time between 10am–2pm or 3pm–7pm.
"""
            else:
                invalid_prompt = f"""
A patient requested a time of {time} on {date}, which is outside the clinic’s working hours (10am–2pm and 3pm–7pm).
Kindly inform them and ask for a new preferred time within working hours.
"""
            speak_invalid = await get_llm_response(invalid_prompt)
            return transcript, text_to_speech(speak_invalid)

        # Ask for email
        ask_email_prompt = """
        Now ask the patient to say their email address, spelling it letter by letter for clarity.
        Tell them to speak clearly and slowly.
        """
        ask_email_text = await get_llm_response(ask_email_prompt)
        tts_path = text_to_speech(ask_email_text)
        return transcript, tts_path

    elif intent == "reschedule":
        return await handle_reschedule_flow(audio_path, date, time)

    elif intent == "cancel":
        return await handle_cancel_flow(audio_path)

    else:
        return transcript, text_to_speech("Sorry, I didn't understand your request. Could you please repeat?")



async def handle_email_spelling(audio_path):
    spelled_email = transcribe_audio(audio_path)
    print("Spelled email (raw):", spelled_email)

    confirm_prompt = f"""
You are an AI assistant confirming an email address.
The patient said: "{spelled_email}". Try to reconstruct the email address.
Only output the email address.
"""
    email = await get_llm_response(confirm_prompt)
    print("Reconstructed Email:", email)

    confirmation_prompt = f"Did you say {email}? Please say yes or no."
    tts_path = text_to_speech(confirmation_prompt)
    return email, tts_path

async def confirm_email_and_book(audio_path, date, time, email):
    confirmation_reply = transcribe_audio(audio_path).lower()
    print("Patient confirmed:", confirmation_reply)

    if "yes" in confirmation_reply:
        from calendar_utils import is_slot_available

        if not is_slot_available(date, time):
            suggest_prompt = f"""
You are an AI scheduling assistant. The slot on {date} at {time} is already booked.
Please suggest the next three available 20-minute slots between 10am–2pm or 3pm–7pm, Monday to Saturday.
Return them in this format:
1. YYYY-MM-DD at HH:MM
2. YYYY-MM-DD at HH:MM
3. YYYY-MM-DD at HH:MM
"""
            suggestions = await get_llm_response(suggest_prompt)
            speak_prompt = f"""
You are a friendly AI assistant for a doctor's clinic. Inform the patient that the slot on {date} at {time} is already booked.
Then suggest these alternative slots:

{suggestions}

Ask the patient to say which one they prefer. Speak in a natural and polite tone.
"""
            speak_text = await get_llm_response(speak_prompt)
            return text_to_speech(speak_text)

        start, end = get_slot_datetime(date, time)
        event = create_event(start, end, "Doctor Appointment", email)
        event_link = event.get("htmlLink") if event else "Unavailable"

        patient_prompt = f"""
You are an AI email assistant. Write a polite confirmation email to a patient.
Also mention them to arrive 10 minutes before your appointment time to fill-up the formalities.
Their appointment is scheduled on {date} at {time}.
Include this event link: {event_link}
Sign off with "Thank you!
and also mention Doctors name and designation name: Dr. Mahajan and M.B.B.S (in italic)"
"""
        patient_email_body = await get_llm_response(patient_prompt)

        doctor_prompt = f"""
You are an AI assistant. Write a brief notification email to a doctor.
Inform them that a patient has booked an appointment on {date} at {time}.
Include the event link: {event_link}
Use a professional tone and sign off with "Regards".
"""
        doctor_email_body = await get_llm_response(doctor_prompt)

        send_email(email, "Your Appointment is Confirmed", patient_email_body)
        send_email("vatsalmahajan0007@gmail.com", "New Appointment Booked", doctor_email_body)

        confirmation_prompt = f"""
You are a friendly voice assistant. Confirm to the patient that their appointment on {date} at {time} is booked, and that a confirmation email has been sent. End with a thank you message.
"""
        confirmation_text = await get_llm_response(confirmation_prompt)
        return text_to_speech(confirmation_text)

    elif "no" in confirmation_reply:
        repeat_email_prompt = """
You are a voice assistant. Apologize that the email address was not correct.
Ask the patient to slowly and clearly spell out their email address again.
"""
        repeat_email_text = await get_llm_response(repeat_email_prompt)
        return text_to_speech(repeat_email_text)

    else:
        unclear_prompt = """
You are a voice assistant. The patient gave an unclear response.
Politely ask them to say "yes" or "no" to confirm their email.
"""
        unclear_text = await get_llm_response(unclear_prompt)
        return text_to_speech(unclear_text)

async def handle_slot_selection(audio_path, email):
    selection_text = transcribe_audio(audio_path)
    print("User selected slot:", selection_text)

    confirm_slot_prompt = f"""
A patient replied: "{selection_text}"
Extract the selected appointment slot in format:
Date: YYYY-MM-DD
Time: HH:MM
"""
    slot_response = await get_llm_response(confirm_slot_prompt)
    print("Extracted slot:", slot_response)

    try:
        date = next(line for line in slot_response.splitlines() if "Date:" in line).split(":", 1)[1].strip()
        time = next(line for line in slot_response.splitlines() if "Time:" in line).split(":", 1)[1].strip()

        # ✅ Validate slot again before booking
        is_valid, reason = is_valid_appointment(date, time)
        if not is_valid:
            invalid_slot_prompt = f"""
The patient selected {date} at {time}, which is invalid due to: {reason}.
Inform the patient about the issue and politely ask them to pick a different time slot within 10am–2pm or 3pm–7pm, Monday to Saturday.
"""
            invalid_response = await get_llm_response(invalid_slot_prompt)
            return text_to_speech(invalid_response)

        return await confirm_email_and_book(audio_path, date, time, email)

    except Exception as e:
        print("Error parsing slot response:", e)
        return text_to_speech("Sorry, I couldn’t understand your selected time. Could you please repeat your choice?")


async def handle_reschedule_flow(audio_path, old_date, old_time):
    # Step 1: Ask for email (spelled)
    ask_email_prompt = """
Please spell the email address used to book your original appointment, letter by letter.
Say it slowly and clearly.
"""
    ask_email_text = await get_llm_response(ask_email_prompt)
    tts_path = text_to_speech(ask_email_text)
    return tts_path  # Wait for next voice input (spelled email)


async def confirm_reschedule_and_book(audio_path, old_date, old_time):
    # Step 1: Transcribe email from the patient's voice
    spelled_email = transcribe_audio(audio_path)
    print("Spelled email (raw):", spelled_email)

    # Step 2: Confirm email with the patient
    confirm_email_prompt = f"""
    The patient said: "{spelled_email}". Is this correct? Please say 'yes' or 'no'.
    """
    email_confirmation = await get_llm_response(confirm_email_prompt)
    
    if email_confirmation.lower() != 'yes':
        return text_to_speech("Please spell your email again.")

    # Step 3: Cancel the existing appointment
    from calendar_utils import find_and_cancel_appointment
    cancelled = find_and_cancel_appointment(spelled_email)

    if not cancelled:
        return text_to_speech("No existing appointment found with that email. Please check and try again.")

    # Step 4: Ask for a new appointment time
    ask_new_time_prompt = """
    The previous appointment has been canceled. Please tell me your new preferred date and time for rescheduling.
    Speak in this format: '2025-04-29 at 10:00 AM'
    """
    ask_new_time_text = await get_llm_response(ask_new_time_prompt)
    tts_path = text_to_speech(ask_new_time_text)

    # Wait for new time input
    new_time = transcribe_audio(audio_path)  # Capture new date and time from the patient
    print("New Time Input:", new_time)

    date, time = await extract_entities(new_time)
    if not date or not time:
        return text_to_speech("Sorry, I couldn’t understand the new date and time. Could you please repeat it?")

    print("Parsed New Date:", date)
    print("Parsed New Time:", time)


    # Step 5: Validate the new time
    is_valid, reason = is_valid_appointment(date, time)
    if not is_valid:
        invalid_prompt = f"""
The patient requested a rescheduling on {date} at {time}, which is outside the available hours or not valid.
Inform the patient of valid hours: Monday–Saturday, 10am–2pm and 3pm–7pm, excluding 2pm–4pm lunch break.
Ask them to choose another time.
"""
        response = await get_llm_response(invalid_prompt)
        return text_to_speech(response)

    # Step 6: Check if the new slot is available
    from calendar_utils import is_slot_available

    if not is_slot_available(date, time):
        conflict_prompt = f"""
The patient wants to reschedule to {date} at {time}, but that slot is already booked.
Politely inform them and suggest three nearby available slots from the calendar.
"""
        response = await get_llm_response(conflict_prompt)
        return text_to_speech(response)

    # Step 7: Book the new appointment
    from calendar_utils import create_event
    start, end = get_slot_datetime(date, time)
    event = create_event(start, end, "Doctor Appointment", spelled_email)
    event_link = event.get("htmlLink") if event else "Unavailable"

    if not event:
        return text_to_speech("There was an issue booking your new appointment. Please try again later.")

    # Step 8: Send confirmation emails to both the patient and doctor
    from email_utils import send_email

    patient_prompt = f"""
You are an AI email assistant. Write a polite "Re-Scheduled confirmation" email to a patient.
Also mention them to arrive 10 minutes before your appointment time to fill-up the formalities.
Their appointment is re-scheduled on {date} at {time}.
Include this event link: {event_link}
Sign off with "Thank you!
and also mention Doctors name and designation name: Dr. Mahajan and M.B.B.S (in italic)"
"""
    patient_email_body = await get_llm_response(patient_prompt)

    doctor_prompt = f"""
You are an AI assistant. Write a brief "Re-Scheduled confirmation" notification email to a doctor.
Inform them that a patient with an email-id {spelled_email} has re-booked an appointment on {date} at {time}.
Include the event link: {event_link}
Use a professional tone and sign off with "Regards".
"""
    doctor_email_body = await get_llm_response(doctor_prompt)

    send_email(spelled_email, "Your Re-Scheduled Appointment is Confirmed", patient_email_body)
    send_email("vatsalmahajan0007@gmail.com", "Appointment has been re-scheduled", doctor_email_body)

    # Final confirmation to the user
    confirmation_text = f"Your appointment has been successfully rescheduled on {date} at {time}. A confirmation email has been sent."
    return text_to_speech(confirmation_text)


async def handle_cancel_flow(audio_path):
    spelled_email = transcribe_audio(audio_path)
    print("Spelled email (raw):", spelled_email)

    confirm_prompt = f"""
You are an AI assistant confirming an email address.
The patient said: "{spelled_email}". Try to reconstruct the email address.
Only output the email address.
"""
    email = await get_llm_response(confirm_prompt)
    print("Reconstructed Email:", email)

    appointment = find_upcoming_appointment_by_email(email)
    if not appointment:
        not_found_prompt = f"""
You are a voice assistant. No upcoming appointment was found for {email}.
Politely inform the patient and suggest they double-check the email or book a new appointment if needed.
"""
        speak_text = await get_llm_response(not_found_prompt)
        return email, text_to_speech(speak_text)

    event_id = appointment['id']
    event_start = appointment['start'].get('dateTime', '')
    event_datetime = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
    date_str = event_datetime.strftime('%Y-%m-%d')
    time_str = event_datetime.strftime('%H:%M')

    if cancel_event(event_id):
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

        cancel_confirm_prompt = f"""
You are a voice assistant. Inform the patient that their appointment on {date_str} at {time_str} has been canceled and a cancellation email has been sent.
End with a polite thank-you message.
"""
        cancel_confirm_text = await get_llm_response(cancel_confirm_prompt)
        return email, text_to_speech(cancel_confirm_text)
    
    else:
        error_prompt = f"""
You are a voice assistant. Inform the patient that there was an error canceling their appointment.
Kindly ask them to try again or contact the clinic directly.
"""
        return email, text_to_speech(await get_llm_response(error_prompt))

async def extract_entities(user_input):
    prompt = f"""
A patient said: "{user_input}"
Extract the date (YYYY-MM-DD) and time (HH:MM, 24-hour).
Only return in this format:
Date: YYYY-MM-DD
Time: HH:MM
"""
    response = await get_llm_response(prompt)
    try:
        date = next(line for line in response.splitlines() if "Date:" in line).split(":", 1)[1].strip()
        time = next(line for line in response.splitlines() if "Time:" in line).split(":", 1)[1].strip()
        return date, time
    except Exception:
        return None, None