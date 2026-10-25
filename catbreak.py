import json, time, random
from datetime import datetime
import ollama
from plyer import notification

MODEL = "gemma3:1b"  # switch to gemma3:4b later to compare

CLIPS = [
    {"url": "https://www.youtube.com/watch?v=J---aiyznGQ", "vibe": "calm"},
    {"url": "https://www.youtube.com/watch?v=5dsGWM5XGdg", "vibe": "chaotic"},
    {"url": "https://www.youtube.com/watch?v=9gT1v7Y9a5A", "vibe": "cute"},
]

FALLBACK = {"vibe": "cute", "message": "Stretch, drink water, then look at this cat."}
INTERVAL = 30  # seconds; use 30 while testing

start = time.time()

def ask_model(hours_worked, clock):
    prompt = f"""It is {clock}. The user has been at their computer for {hours_worked:.1f} hours.
Choose the best cat video vibe from: calm, chaotic, cute.
Write a short, funny, gentle nudge to stretch or drink water.
Reply only as JSON: {{"vibe": "...", "message": "..."}}"""
    r = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}], format="json")
    return json.loads(r["message"]["content"])

while True:
    hours = (time.time() - start) / 3600
    try:
        out = ask_model(hours, datetime.now().strftime("%I:%M %p"))
        if "vibe" not in out or "message" not in out:
            out = FALLBACK
    except Exception:
        out = FALLBACK
    options = [c for c in CLIPS if c["vibe"] == out["vibe"]] or CLIPS
    clip = random.choice(options)
    notification.notify(title="Cat break", message=f'{out["message"]}\n{clip["url"]}', timeout=20)
    print(datetime.now(), out, clip["url"])
    time.sleep(INTERVAL)