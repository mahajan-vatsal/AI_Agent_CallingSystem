from calendar_utils import create_event, get_slot_datetime

start, end = get_slot_datetime("2025-04-25", "10:40")
link = create_event(start, end, "Checkup with Dr. Mahajan", "patient@example.com")
print("Event created:", link)
