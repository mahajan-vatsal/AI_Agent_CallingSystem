import asyncio
from appointment_schedule import (
    handle_patient_reply,
    handle_email_spelling,
    confirm_email_and_book,
    handle_cancel_flow,
    confirm_email_and_reschedule,
    extract_missing_date_or_time
)
from calendar_utils import get_calendar_service, CALENDAR_ID

service = get_calendar_service()
calendar_id = CALENDAR_ID

async def main():
    print("🎧 Welcome to Test Mode for AI Appointment Scheduler.\n")

    intent, transcript, date, time = None, "", "", ""

    while not intent:
        audio_path = input("🔈 Upload/replace patient request audio (.wav) and enter the path: ").strip()

        async for detected_intent, detected_transcript, detected_date, detected_time, response_audio in handle_patient_reply(audio_path):
            print(f"📝 Transcript: {detected_transcript}")
            print(f"🧠 LLM Detected → Intent: {detected_intent}, Date: {detected_date}, Time: {detected_time}")

            if detected_intent in ["schedule", "reschedule", "cancel"]:
                intent = detected_intent
                date = detected_date
                time = detected_time
                break

        if not intent:
            print("⚠️ Could not understand intent. Try again.")


    # ========== CANCEL FLOW ==========
    if intent == "cancel":
            print("\n=== ❌ Cancel Flow ===")
            max_attempts = 3
            attempts = 0

            while attempts < max_attempts:
                email_audio = input("\n🔤 Upload patient email spelling audio: ").strip()
                email = None

                async for captured_email, _ in handle_email_spelling(email_audio):
                    if captured_email:
                        email = captured_email
                        print(f"✅ Email Captured: {email}")
                        break
                    else:
                        print("⚠️ Could not extract email. Try again.")

                if not email:
                    attempts += 1
                    continue

                confirm_audio = input(f"\n✅ Upload Yes/No confirmation for email '{email}': ").strip()

                async for status, returned_email, audio_response in handle_cancel_flow(email_audio, confirm_audio):
                    if audio_response:
                        print("📢 Speaking:", audio_response)

                    if status == "repeat_email":
                        print(f"🔁 Email rejected by patient. Attempt {attempts+1}/{max_attempts}")
                        attempts += 1
                        break

                    elif status == "not_found":
                        print(f"❌ No appointment found for: {returned_email}")
                        return

                    elif status == "canceled":
                        print(f"✅ Appointment canceled for: {returned_email}")
                        return

                    elif status == "error":
                        print(f"❗ Unexpected error for: {returned_email}")
                        return

                else:
                    print("⚠️ Unexpected issue during cancel flow.")
                    break

            print("⛔ Max attempts reached. Cancelation flow ended.")
            return

    # ========== RESCHEDULE FLOW ==========
    if intent == "reschedule":
            print("\n=== 🔄 Reschedule Flow ===")
            max_attempts = 3
            attempts = 0
            success = False
            if not date and not time:
                print("🗓️ Assistant says: Please say your preferred date and time.")
                datetime_audio = input("🎤 Upload audio with patient's response for both date and time: ").strip()
                new_date, new_time, _ = await extract_missing_date_or_time(datetime_audio)
                if new_date:
                    date = new_date
                    print(f"✅ Captured Date: {date}")
                else:
                    print("❌ Could not extract date.")
                if new_time:
                    time = new_time
                    print(f"✅ Captured Time: {time}")
                else:
                    print("❌ Could not extract time.")
            else:
                if not date:
                    print("🗓️ Assistant says: Please say your preferred date.")
                    date_audio = input("🎤 Upload audio with patient's date response: ").strip()
                    new_date, _, _ = await extract_missing_date_or_time(date_audio)
                    if new_date:
                        date = new_date
                        print(f"✅ Captured Date: {date}")
                    else:
                        print("❌ Could not extract date.")

                if not time:
                        print("🗓️ Assistant says: Please say your preferred time.")
                        time_audio = input("🎤 Upload audio with patient's time response: ").strip()
                        _, new_time, _ = await extract_missing_date_or_time(time_audio)
                        if new_time:
                            time = new_time
                            print(f"✅ Captured Time: {time}")
                        else:
                            print("❌ Could not extract time.")

            print(f"\n🔁 Attempting to reschedule to {date} at {time}")

            while attempts < max_attempts:
                email_audio = input("\n🔤 Upload patient email spelling audio: ").strip()
                email = None

                async for captured_email, _ in handle_email_spelling(email_audio):
                    if captured_email:
                        email = captured_email
                        print(f"✅ Email Captured: {email}")
                        break
                    else:
                        print("⚠️ Could not extract email. Try again.")

                if not email:
                    attempts += 1
                    continue

                confirm_audio = input(f"\n✅ Upload Yes/No confirmation for email '{email}': ").strip()

                async for result, _,  response_audio in confirm_email_and_reschedule(
                    confirm_audio, date, time, email, service, calendar_id
    ):
                    if result == "reschedule_booked":
                        print("✅ Rescheduled Successfully.")
                        success = True
                    elif result == "reschedule_repeat_email":
                        print("🔁 Retrying email spelling.")
                        attempts += 1
                    elif result == "cancel_not_found":
                        print("❌ No appointment found to reschedule.")
                        break
                    else:
                        print("⚠️ Could not reschedule. Trying again...")
                        attempts += 1
                if success:
                    break

    

        

    # ========== SCHEDULE FLOW ==========
    if intent == "schedule":
            print("\n=== 📅 Schedule Flow ===")
            max_attempts = 3
            attempts = 0

            while attempts < max_attempts:
                email_audio = input("\n🔤 Upload patient email spelling audio: ").strip()
                email = None

                async for captured_email, _ in handle_email_spelling(email_audio):
                    if captured_email:
                        email = captured_email
                        print(f"✅ Email Captured: {email}")
                        break
                    else:
                        print("⚠️ Could not extract email. Try again.")

                if not email:
                    attempts += 1
                    continue

                confirm_audio = input(f"\n✅ Upload Yes/No confirmation for email '{email}': ").strip()

                async for result, response_audio in confirm_email_and_book(
                    confirm_audio, date, time, email, service, calendar_id
        ):
                    if response_audio:
                        print("📢 Speaking:", response_audio)

                    if result == "booked":
                        print("✅ Appointment booked and confirmation sent!")
                        return

                    elif result == "email_already_used":
                        print("⛔ Appointment already exists for this email.")
                        return

                    elif result == "repeat_email":
                        print("🔁 Patient said NO. Retrying email spelling...")
                        attempts += 1
                        break

                    else:
                        print("⚠️ Could not understand confirmation. Try again.")
                        attempts += 1
                        break

            print("⛔ Max attempts reached. Scheduling failed.")
            return

if __name__ == "__main__":
    asyncio.run(main())













#Would you like me to also show you a bonus:
#how to simulate different flows like:

#Patient says wrong email first and repeats it again
#Patient asks for a Sunday appointment and AI politely denies



#Test-cases:
# 1. Test with a clear audio file where the patient clearly states the date, time, and email. (e.g, a normal appointment request)
# 2. Test with a noisy audio file where the patient states the date, time, and email but with background noise.
# 3. Test with a file where the patient spells their email correctly.
# 4. Test with a file where the patient spells their email incorrectly.
# 5. Test with a file where the patient says "yes" to confirm the appointment.
# 6. Test with a file where the patient says "no" to confirm the appointment.
# 7. Test with a file where the patient asks for a Sunday appointment.
# 8. Test with a file where the patient asks for an appointment outside of business hours.
# 9. Test with a file where the patient asks for an appointment but doesn't provide a date or time.(e.g, "I want to book an appointment.")
# 10. Test with a file where the patient provides a date and time but doesn't confirm the appointment.
# 11. Test with a file where the patient provides a date and time but the appointment slot is already booked.
# 12. Test with a file where the patient provides a date and time but the appointment is outside of business hours.
# 13. Test with a file where the patient doesn't provides 'yes' or 'no' to confirm the appointment.



#Glitch:
# 1. Confirm_no audio output is not that much accurate.
# 2. Confirmation_audio output is not that much accurate.
# 3. calendar event link double aari h patient yaa doctor ke email pe.
# 4. wrong_time_audio dene k bad jb right audio de rha hun toh woh phir se wrong_time_audio hi transcribe kar raha hai.



#Result:
# All the test case runs perfectly fine. Only one thing is missing that's a max_retry limit. That should be added in the test_agent.py file.
#audio_scheduleinput/patient_request.wav

#I have already implemented some to cancel multiple appointments by requiring the patient to confirm both email and the specific date/time. Here's the code you can analyse. and let me know where to we need to make the changes:


#Patient's date: Sorry, we couldn't understand your request. Please try calling again later.
#Patient's time: Asking for E-mail address.
#Email spelling: Please say your email address. which is correct, and as per the flow
#Yes/No confirmation: This confirmation asking is correct, but should be asked after The model reconstructs the email address and then ask for yes or no.
# In the above output, the loop is running such number of times? After extracting the intent the loop should be stopped and the next step if intent == 'reschedule' should be started.
#Why the loop is not breaking after giving the confirmation?