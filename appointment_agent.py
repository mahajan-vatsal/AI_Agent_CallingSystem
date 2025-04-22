import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

async def process_call_logic(data):
    # Use an LLM to generate a warm greeting
    greeting_prompt = """
You are a friendly and professional assistant at a doctor's clinic. 
Greet the patient and ask if they want to schedule, reschedule, or cancel an appointment.
Keep it clear and under 30 words.
"""

    llm_response = await get_llm_response(greeting_prompt)
    
    # Respond in Exotel's XML format
    return f"""
    <Response>
        <Say>{llm_response}</Say>
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
