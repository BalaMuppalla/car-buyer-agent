# Roarwell Motors: Car Buyer Agent

A car-shopping website with **Alex**, a friendly AI agent who helps you pick a car, explains specs, works out
payments and APR, negotiates a price, and books a test drive. It started as a small terminal chatbot and grew,
step by step, into a full website. Everything uses **free** tools.

> **Demo only.** No real cars are sold, no payments are taken, and all rates and prices are examples.
> Car makers' names are used only as labels. This project is not affiliated with any car maker.

## What it does
- 45 cars (modern and classic) with real photos from Wikimedia Commons, specs, resale value and yearly fuel cost
- Filters, shortlist, side-by-side compare, payment calculator, hover tooltips
- **Alex**, an AI agent that uses tools: search the lot, look up a car, compare, estimate payments, show cars on
  the page, open a car, save to your shortlist, show payment options, negotiate, close a (demo) deal, book a test drive
- A cinematic 3D intro: headlights in the dark, glass shatters, a supercar skids onto a sunrise beach road
- Sound effects made in the browser (no audio files)

## How it is built
| Piece | Technology |
|---|---|
| AI brain | Groq free model `openai/gpt-oss-20b` through LangChain, with free backups on Groq, Cerebras and OpenRouter |
| Agent logic | `agent.py`: a **LangGraph** graph with a `call_model` node and a `run_tool` node. The AI asks for a tool, Python runs it, the AI answers |
| Server | FastAPI + uvicorn (`server.py`) |
| Website | plain HTML, CSS, JavaScript in `web/` |
| 3D intro | three.js (copied into `web/vendor/`) and a 3D car model |
| Photos | Wikipedia / Wikimedia Commons, cached in `photo_cache/` |

## Files
- `cars.py`: the 45 cars and helper functions (`slugify`, `resale_value`, `yearly_fuel_cost`)
- `specs.py`: specs table for every car
- `traits.py`: what each car is good for (towing, cargo, snow, camping...). Approximate.
- `agent.py`: Alex: tools, system prompt, parser, the agent loop, the deal tools
- `server.py`: the API and the web server
- `photos.py`: finds and caches car photos
- `graph.py`, `app.py`, `ui.py`: the earlier terminal and Streamlit versions (still work)
- `check_photos.py`, `check_alex.py`, `list_models.py`: small diagnostic scripts
- `web/`: the website (`index.html`, `app.js`, `alex.js`, `intro3d.js`, ...)

## Run it
1. Get a free key at https://console.groq.com
2. In the project folder:
   ```
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   cp .env.example .env        # then open .env and paste your key after GROQ_API_KEY=
   .venv/bin/python -m uvicorn server:app --reload
   ```
3. Open http://127.0.0.1:8000. Add `?intro=1` to replay the intro, `?intro=0` to skip it.

## How Alex's deal-making works (and why it is safe)
The AI never decides a price. Python does.
- `payment_options` makes a loan table for 36/48/60/72 months with example APRs by credit band.
- `negotiate` accepts or counters. Alex has a hidden floor (about 94% of sticker for modern cars, 96% for classics)
  that is enforced in Python, so the AI cannot be talked below it. At the floor he offers perks (term, down
  payment, test drive) or a cheaper car instead.
- `close_deal` needs a clear yes from the customer and refuses any price below what was agreed. It saves a demo
  record to `deals.json`.
- He never asks for card numbers, bank details or an SSN.

---

# The build story: every step, every mistake, every fix

This is the honest log of how it was made, including everything that broke.

## 1. The first version: a terminal chatbot (LangGraph)
We built a step-by-step question bot: greet, ask the name, then passengers, fuel, budget, commute, favorite
brand, modern or classic. LangGraph runs it as a graph of steps (nodes) with a shared memory (state).
It first shows the favorite brand's cars, then the others sorted by resale value.

## 2. Mistakes while setting up (and the fixes)
| Problem | Cause | Fix |
|---|---|---|
| Could not create files: read-only folder | Project was in a protected location | Moved the project to `~/Documents/car-buyer-agent` |
| `GROQ_API_KEY` not found | `.env` lacked the exact `GROQ_API_KEY=` prefix | Wrote the line exactly as `GROQ_API_KEY=gsk_...` |
| `ModuleNotFoundError` for libraries | Packages not installed in the virtual environment | `.venv/bin/pip install ...` (now in `requirements.txt`) |
| Model 404 | The model name we first used no longer existed on Groq | `list_models.py` showed the live names; switched to `openai/gpt-oss-20b` |
| `tool_use_failed` (structured output) | The free model was unreliable with built-in structured output | Asked for plain JSON in the prompt and parsed it ourselves |
| Endless loops while looking up cars | The AI kept calling tools | Added a step limit (`MAX_TOOL_STEPS`) |

## 3. More features, step by step
Vintage cars (a 1969 Mustang Mach 1), detail lookup by short name ("Tacoma"), the "Are you choosing this car?"
spec table ending with "Let's go for a spin!", a Streamlit version (`ui.py`), then the website: filters,
shortlist, compare, payment calculator and hover tips. The user asked for a better name and look; the site became
**Roarwell Motors** with a dark theme.

## 4. Website problems and fixes
- **"Website not found"**: the `web` folder did not exist on the user's machine. Fix: create it and copy files in.
- **Cartoon cars looked made for children**: replaced them with real photos, with a sleek drawing as backup.
- **All photos 404 and Alex failing**: `slug.py` was missing, so imports failed. Fix: moved `slugify()` into
  `cars.py`. Photos were also made more robust: Wikipedia summary, then the Commons file, only accepting Commons
  URLs, license and author credit read from Commons, cached on disk, retries on rate limits, short "miss" memory.
- **Browser asked for `/favicon.ico`** (harmless 404): added an icon.

## 5. Turning Alex into a real agent (and moving it onto LangGraph)
Alex got tools (search, get details, compare, payments, show/open/save on the page). Because the free model fails
at built-in tool calls, we invented a plain-text protocol: the model writes `ACTION tool {json}` or
`REPLY: text` (plus `CHIPS:` and `REMEMBER:`). Python parses it and runs the tool. The loop is a LangGraph graph: `call_model` -> (conditional edge) -> `run_tool` -> back to `call_model`, or END when the AI has a final answer. We first wrote the loop by hand, then ported it to LangGraph to match the project's problem statement.

**The `output_parse_failed` bug.** Sometimes the model "thought out loud" (for example, "The user says sienna...") and Groq rejected it with a 400 error. Fix: rescue usable text from the error, otherwise ask again with a firm reminder (up to 3 tries), then fall back to a friendly message. We also set a low reasoning effort.

**Model choice.** If format errors continue, try a larger free Groq model by setting `ALEX_MODEL` in `.env` (for example `ALEX_MODEL=openai/gpt-oss-120b`).

**The function-call JSON bug.** Alex sometimes printed raw JSON like `{"name": "search_cars", "arguments": ...}`
instead of answering. Cause: the model sometimes used a "function call" shape, and Groq sometimes rejected it with
a 400 error holding the text in `failed_generation`. Fix: the parser understands several JSON shapes, `call_model`
rescues `failed_generation`, raw JSON is never shown to the customer, and a friendly fallback message is used if
the output is unreadable. Tests cover all of this.

## 6. The cinematic 3D intro
We wanted a real-looking car, sun and parked cars. A free CC-BY 3D model ("Car Concept" by Eric Chadwick) is rendered
with three.js: dark scene with glowing headlights, the car charges the screen, the glass shatters, and a hero car
skids in on a sunrise road lined with parked cars. Bugs along the way:
- **White glare over everything**: spotlights too close and bright. Moved and dimmed them, darkened the floor.
- **Car showed its back**: the model's nose pointed the wrong way. Added an automatic check that flips it.
- **Car passed through the camera**: reduced the charge acceleration.
- **Black frame / washed-out scene**: tuned sun glow, bloom threshold and exposure; `PCFSoftShadowMap` no longer exists in the
  new three.js, so `PCFShadowMap` is used.
- **Delay before the glass broke and a laggy skid**: the sunrise scene was being prepared at the moment of the crash.
  Fix: draw it once off-screen early, make the glass snapshot smaller, play the sound first, reuse smoke sprites.

## 7. Deal-making and a pop-up Alex
Alex now talks payments, APR and price, negotiates with a Python-enforced floor, closes a demo deal, and books a test drive,
with confirmation cards and confetti. Choosing a car makes Alex pop up and offer a deal or test drive.
A bug found on the way: the "Ask Alex" button did nothing because `Alex` was not attached to `window`. Fixed.

## 8. Testing
Fake-AI tests check the whole agent without the internet: parsing, tool use, deals and the negotiation floor.
Browser tests (Playwright) click through the site and screenshot it.

## Credits and legal
- Car photos: Wikimedia Commons, each with its own license and author shown in the site.
- 3D car model: "Car Concept" by Eric Chadwick, CC BY 4.0 (from the Khronos glTF Sample Assets).
- three.js: MIT license.
- Brand names appear only as labels for the cars. Not affiliated with any car maker.
- Prices, APRs and payments are examples. Alex is not a financial advisor.

## Roadmap
1. **Now**: browsing, Alex, deals, test-drive booking, 3D intro
2. **Next**: trade-in estimator, insurance estimate, saved deals page, a share link for your shortlist
3. **Later**: user accounts, a real database, voice chat with Alex, 360-degree car views, a dealer dashboard
4. **Dream**: connect to real inventory and real lenders (with legal review)

**Free daily limits (error 429).** Every free model has its own daily token allowance. When Alex's main model runs out, he switches automatically, in this order: other Groq models, then Cerebras, then OpenRouter. A backup is only used if its key is in `.env` (`CEREBRAS_API_KEY`, `OPENROUTER_API_KEY`; both are free, see `.env.example`). Models that just hit a limit are skipped for 5 minutes so replies stay fast.
