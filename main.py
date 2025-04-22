from fastapi import FastAPI, Request
from fastapi.responses import Response
from appointment_agent import process_call_logic

app = FastAPI()

@app.post("/webhook/incoming-call")
async def handle_incoming_call(request: Request):
    # For now, Exotel just expects an XML response
    body_bytes = await request.body()
    response_xml = await process_call_logic(body_bytes)
    return Response(content=response_xml, media_type="application/xml")
