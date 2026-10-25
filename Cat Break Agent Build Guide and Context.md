# Cat Break Agent: Build Guide and Context

A step-by-step guide for the Hacktoberfest Open-Source AI Challenge (Week 3: Slow and Steady), plus a context block you can paste into a new Claude chat on another account.

## Part 1: Context to paste into a new chat

Copy everything in this section into the first message of the new conversation.

> I'm entering the DEV Hacktoberfest Open-Source AI Challenge, Week 3: "Slow and Steady". Theme: build something with open-weight models or open-source AI that does work so I don't have to. Submissions are due October 25, 2026 at 11:59 PM PDT, so I'm short on time. The judges weight the written post most heavily, then relevance to the theme (open-source AI must be at the core), creativity, and technical execution. The post must explain why open innovation matters for what I built. There's an optional "Best Use of Gemma" partner category.
>
> My project is the Cat Break Agent. Every hour, a small local open-weight model (Gemma, run through Ollama) looks at the time and how long I've been at my computer, picks a cat video vibe (calm, chaotic, or cute), and writes a short funny nudge to stretch and drink water. A Python script sends it as a desktop notification with a cat video link.
>
> My setup: laptop with 8 GB RAM, no powerful GPU. I'm a beginner and not sure what open weights means beyond "models you can download and run yourself." Plan: get it working with gemma3:1b first, then try gemma3:4b and compare the two in my post. I already have a draft script (Python, ollama and plyer libraries, JSON output with a fallback if the model returns bad JSON). Please help me with whichever step I'm on, and later help me write the DEV post.

## Part 2: Quick concepts

- **Open weights:** the company published the trained model files, so you can download and run the model on your own computer. No API key, no per-request cost, and nothing you type leaves your machine. Examples: Gemma, Llama, DeepSeek.
- **Gemma:** Google's family of small open-weight models. Hacktoberfest isn't only about Gemma; "Best Use of Gemma" is just one optional prize category you can also enter.
- **Ollama:** a free program that downloads and runs open-weight models locally.
- **What the model does here:** it only outputs text, but that text is a decision (which vibe) plus a joke. Normal Python code handles the scheduling, notifications, and link picking.

## Part 3: Build steps (about 1 hour)

### Step 1: Install Ollama

Download it from ollama.com and install it. Then open a terminal (Command Prompt or PowerShell on Windows) and check it works:

```
ollama --version
```

### Step 2: Download a model

Start with the small one so you get something working fast:

```
ollama pull gemma3:1b
```

That's roughly 800 MB. Confirm the tag names at ollama.com/library/gemma3 in case they've changed. Later you can try the better one (about 3 GB, fits in 8 GB RAM if you close your browser tabs):

```
ollama pull gemma3:4b
```

If the laptop struggles, `gemma3:270m` is a tiny fallback with weaker jokes.

### Step 3: Install the Python libraries

From the project folder, create a virtual environment and install the dependencies:

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Select `.venv\Scripts\python.exe` as the VS Code Python interpreter so Pylance and the script use the same environment.

### Step 4: Collect cat videos

Find 10 to 20 funny cat video links (YouTube is fine). Tag each as `calm`, `chaotic`, or `cute`. Aim for at least 3 per vibe.

### Step 5: Save the script

Create a file called `catbreak.py` and paste this in. Replace the example links with your own.

```python
import json, time, random
from datetime import datetime
import ollama
from plyer import notification

MODEL = "gemma3:1b"  # switch to gemma3:4b later to compare

CLIPS = [
    {"url": "https://youtube.com/watch?v=REPLACE1", "vibe": "calm"},
    {"url": "https://youtube.com/watch?v=REPLACE2", "vibe": "chaotic"},
    {"url": "https://youtube.com/watch?v=REPLACE3", "vibe": "cute"},
]

FALLBACK = {"vibe": "cute", "message": "Stretch, drink water, then look at this cat."}
INTERVAL = 3600  # seconds; use 30 while testing

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
```

### Step 6: Test it

Change `INTERVAL = 3600` to `INTERVAL = 30`, then run:

```
python catbreak.py
```

You should see a notification within a few seconds (the first reply can take longer while the model loads). Let it run 3 or 4 rounds and note what the model gets right and wrong.

**If something breaks:**

- *Connection error:* Ollama isn't running. Open the Ollama app, or run `ollama serve` in another terminal.
- *Model not found:* the name in `MODEL` doesn't match what you pulled. Run `ollama list` to see exact names.
- *No notification appears:* check your OS notification or Focus Assist settings. The `print` line still shows the output in the terminal, which is enough for a demo.
- *Laptop freezes:* close other apps, or drop to a smaller model.

### Step 7: Compare 1B and 4B

Pull `gemma3:4b`, set `MODEL = "gemma3:4b"`, and run the same test. Write down for each model: how long a reply takes, how often the JSON was broken, and whether the jokes were funnier. This comparison is great material for your post.

### Step 8: Capture your demo

Set `INTERVAL` back to 3600. Screen-record a notification popping up (Windows: Win+Shift+S for a screenshot, or Xbox Game Bar with Win+G for video). A short GIF or clip is plenty.

## Part 4: Write the DEV post

The write-up is weighted most heavily, so give it at least 30 minutes. Use the Slow and Steady submission template linked in the challenge post. Suggested structure:

1. **What I built:** one or two sentences. An hourly local AI agent that picks the right cat video and nudges me to take a break.
2. **Who it's for and what effort it saves:** people who sit for hours and forget to move, with no need to scroll for a good video.
3. **Demo:** your screen recording or screenshots.
4. **How it works:** Ollama, Gemma, and the Python script in a few short paragraphs, with the key code.
5. **Why open weights mattered:** it works offline, nothing about my work habits leaves my laptop, and an hourly job costs nothing. Say where this beat a closed API.
6. **What went wrong (be honest):** the 1B model's broken JSON, the fallback you added, and the 1B vs 4B comparison.
7. **What's next:** ideas such as detecting real idle time, a local vision model to filter videos, or a phone notification.

Tags to use: `#devchallenge`, `#hf26challenge`, `#hacktoberfest`, `#productivity`. Also check the partner prize list: if you used Gemma, enter the "Best Use of Gemma" category too.

## Part 5: Final checklist

- [ ] Ollama installed and model pulled
- [ ] Script runs and shows at least one notification
- [ ] 1B vs 4B notes written down
- [ ] Screen recording or screenshots saved
- [ ] Post written from the submission template, with tags added
- [ ] Submitted before **11:59 PM PDT on October 25**

If you run out of time, ship the 1B version and skip the comparison. A working project with an honest, well-written post beats an unfinished ambitious one.
