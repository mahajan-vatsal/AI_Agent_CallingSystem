import asyncio
from appointment_schedule import handle_patient_reply, handle_email_spelling, confirm_email_and_book

async def main():
    print("Welcome to Test Mode for Appointment Scheduler.\n")

    # Step 1: Get valid patient intent (schedule, reschedule, cancel)
    while True:
        audio_path = input("Upload or replace your patient request audio (.wav) and enter the path: ").strip()
        result_found = False

        async for transcript, date, time, response_audio in handle_patient_reply(audio_path):
            if transcript and date and time:
                print(f"✅ Understood Request: {transcript}, Date: {date}, Time: {time}")
                result_found = True
                break
            else:
                print("⚠️ LLM couldn't parse the request properly.")
                break  # Break inner async loop so we can retry with new audio_path

        if result_found:
            break  # Exit retry loop once result is valid

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
                break  # Break async loop so we can re-input

        if email_found:
            break

    # Step 3: Confirm email and finalize booking
    while True:
        audio_path = input(f"\nUpload Yes/No confirmation for email '{email}': ").strip()
        async for result, response_audio in confirm_email_and_book(audio_path, date, time, email):
            if result == "booked":
                print("✅ Appointment successfully booked and confirmation emails sent!")
                return
            elif result == "repeat_email":
                print("🔁 Patient said NO. Repeating email spelling process.")
                break  # Break inner loop and re-do email collection
            else:
                print("⚠️ Unclear Yes/No response. Try again.")
                break  # Break and re-confirm

        if result == "repeat_email":
            # Recollect email
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