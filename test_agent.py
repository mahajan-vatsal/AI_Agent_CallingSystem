import asyncio
from appointment_agent import (
    handle_patient_reply,
    handle_email_spelling,
    confirm_email_and_book
)

# Paths to your simulated patient audio recordings
AUDIO_REQUEST_PATH = "audio1_request_appointment.wav"
AUDIO_EMAIL_SPELLING_PATH = "audio2_spelled_email.wav"
AUDIO_CONFIRM_EMAIL_PATH_YES = "audio3_confirm_yes.wav"
AUDIO_CONFIRM_EMAIL_PATH_NO = "audio3_confirm_no.wav"

async def run_test_flow():
    print("\n--- STEP 1: Handle patient intent (appointment request) ---")
    transcript, ask_email_tts = await handle_patient_reply(AUDIO_REQUEST_PATH)
    print("Transcript:", transcript)
    print("TTS to patient:", ask_email_tts)

    input("Play ask_email_tts to patient, then press Enter after receiving spelled email...\n")

    print("\n--- STEP 2: Handle patient email spelling ---")
    email, confirm_tts = await handle_email_spelling(AUDIO_EMAIL_SPELLING_PATH)
    print("Email from LLM:", email)
    print("TTS to patient:", confirm_tts)

    input("Play confirm_tts to patient, then press Enter after receiving their confirmation reply...\n")

    print("\n--- STEP 3: Confirm email and book appointment ---")
    final_tts = await confirm_email_and_book(AUDIO_CONFIRM_EMAIL_PATH_YES, date="2025-04-29", time="11:00", email=email)
    print("Final TTS to patient:", final_tts)

if __name__ == "__main__":
    asyncio.run(run_test_flow())
