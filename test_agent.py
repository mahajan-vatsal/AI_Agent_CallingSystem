import asyncio
from appointment_schedule import (
    handle_patient_reply,
    handle_email_spelling,
    confirm_email_and_book,
    handle_cancel_flow
)

from calendar_utils import get_calendar_service, CALENDAR_ID 

service = get_calendar_service()
calendar_id = CALENDAR_ID

async def main():
    print("Welcome to Test Mode for Appointment Scheduler.\n")

    # Step 1: Get valid patient intent (schedule, reschedule, cancel)
    while True:
        audio_path = input("Upload or replace your patient request audio (.wav) and enter the path: ").strip()
        result_found = False

        async for intent, transcript, date, time, response_audio in handle_patient_reply(audio_path):
            if intent in ["schedule", "reschedule", "cancel"]:
                print(f"✅ Understood Intent: {intent}, Transcript: {transcript}, Date: {date}, Time: {time}")
                result_found = True
                break
            else:
                print("⚠️ LLM couldn't parse the request properly.")
                break  # Retry with new audio_path

        if result_found:
            break

    # ➤ Cancel Flow
    if intent == "cancel":
        print("\n=== 🟡 Cancel Flow ===")
        max_attempts = 3
        attempts = 0
        email_confirmed = False

        while attempts < max_attempts and not email_confirmed:
            email_audio_path = input("🔤 Please provide email spelling audio path: ").strip()
            confirm_audio_path = input("✅ Please provide confirmation audio path (yes/no): ").strip()

            async for status, returned_email, audio_response in handle_cancel_flow(email_audio_path, confirm_audio_path):
                if audio_response:
                    print("📢 Speaking:", audio_response)

                if status == "repeat_email":
                    attempts += 1
                    print(f"🔁 Patient rejected email confirmation. Attempt {attempts}/{max_attempts}.")
                    break  # Ask for new audio inputs

                elif status == "not_found":
                    print(f"❌ No appointment found for email: {returned_email}")
                    email_confirmed = True  # Stop further attempts
                    break

                elif status == "canceled":
                    print(f"✅ Appointment canceled for email: {returned_email}")
                    email_confirmed = True
                    break

                elif status == "error":
                    print(f"❗ Error occurred while canceling for: {returned_email}")
                    email_confirmed = True
                    break
            else:
                # If generator didn't yield anything (shouldn't happen)
                print("⚠️ Unexpected end of cancellation flow.")
                break

        if attempts == max_attempts:
            print("⛔ Max attempts reached. Cancelation flow ended.")
        return  # Stop after cancel flow

    # ➤ Schedule/Reschedule Flow
    # Step 2: Get email from spelling
    while True:
        audio_path = input("\nUpload patient email spelling audio and enter the path: ").strip()
        email_found = False

        async for email, response_audio in handle_email_spelling(audio_path):
            if email:
                print(f"✅ Captured Email: {email}")
                email_found = True
                break
            else:
                print("⚠️ Could not extract email. Try again.")
                break  # Retry

        if email_found:
            break

    # Step 3: Confirm email and finalize booking
    while True:
        audio_path = input(f"\nUpload Yes/No confirmation for email '{email}': ").strip()
        async for result, response_audio in confirm_email_and_book(audio_path, date, time, email, service, calendar_id):
            
            if response_audio:
                print("📢 Speaking:", response_audio)

            if result == "booked":
                print("✅ Appointment successfully booked and confirmation emails sent!")
                return
            
            elif result == "email_already_used":
                print("⛔ Appointment already exists for this email. Cannot book another.")
                return
            
            elif result == "repeat_email":
                print("🔁 Patient said NO. Repeating email spelling process.")
                break  # Break to redo spelling

            else:
                print("⚠️ Unclear Yes/No response. Try again.")
                break

        if result == "repeat_email":
            while True:
                audio_path = input("Upload corrected spelled email audio: ").strip()
                async for email, response_audio in handle_email_spelling(audio_path):
                    if email:
                        print(f"✅ Captured New Email: {email}")
                        break
                    else:
                        print("⚠️ Could not extract email. Try again.")
                        break
                else:
                    continue
                break

        print("\n✅ Test Session Completed.")

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

