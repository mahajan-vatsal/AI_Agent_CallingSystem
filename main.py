from fastapi import FastAPI, Request
from fastapi.responses import Response
import aiohttp
import uuid
from appointment_agent import process_call_logic, handle_recorded_audio

app = FastAPI()

@app.post("/webhook/incoming-call")
async def handle_incoming_call(request: Request):
    # Handles the initial incoming call
    body_bytes = await request.body()
    response_xml = await process_call_logic(body_bytes)
    return Response(content=response_xml, media_type="application/xml")

@app.post("/webhook/handle-recording")
async def handle_recording(request: Request):
    # Handles the audio file after recording ends
    data = await request.form()
    recording_url = data.get("RecordingUrl")

    if not recording_url:
        return Response(content="<Response><Say>No recording received.</Say></Response>", media_type="application/xml")

    audio_filename = f"recording_{uuid.uuid4().hex}.wav"
    audio_path = f"/tmp/{audio_filename}"

    async with aiohttp.ClientSession() as session:
        async with session.get(recording_url) as resp:
            if resp.status == 200:
                with open(audio_path, 'wb') as f:
                    f.write(await resp.read())
            else:
                return Response(content="<Response><Say>Could not fetch recording.</Say></Response>", media_type="application/xml")

    # Process it through your AI logic
    response_audio_url = await handle_recorded_audio(audio_path)

    if response_audio_url:
        return Response(content=f"""
<Response>
    <Play>{response_audio_url}</Play>
</Response>
        """, media_type="application/xml")
    else:
        return Response(content="<Response><Say>There was a problem processing your request.</Say></Response>", media_type="application/xml")
