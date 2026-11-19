"""agent.py - Alex as a real AI AGENT.

What is the difference from graph.py (the question-and-answer bot)?
  * graph.py follows a fixed script: ask question 1, then 2, then 3...
  * agent.py lets the AI decide what to do. If you ask "can I tow a boat with the Tacoma?", Alex looks up
    that car with a TOOL, reads the result, then answers in his own words. He can also search the lot,
    compare cars, work out payments, and control the website (show cars, open one, save one).

The loop below is built as a LANGGRAPH graph (see build_graph). How the loop works (this is the heart of every agent):
  1. We send the AI the conversation plus a list of tools it may use.
  2. The AI answers with JSON: either {"tool": ..., "args": ...} ("please run this") or {"say": ...} ("I'm done").
  3. If it asked for a tool, WE run it in Python and send the result back. Go to step 2.
  4. When it says {"say": ...}, that is the reply the customer sees.

We use plain JSON text for this instead of the model's built-in tool-calling, because the free Groq model
was unreliable at built-in tool calls (remember the 'tool_use_failed' error?). Plain JSON works every time.
"""
import json
import os
import random
import re
import time
from pathlib import Path

from cars import CARS, BRANDS, FUEL_PRICE, is_vintage, resale_value, yearly_fuel_cost, slugify
from specs import spec_rows
from traits import profile

MAX_TOOL_STEPS = 5
DEBUG = os.environ.get("ALEX_DEBUG", "1") != "0"      # prints what the AI really wrote, to help us fix problems
HERE = Path(__file__).parent
DEALS_FILE = HERE / "deals.json"
DRIVES_FILE = HERE / "test_drives.json"

# DEMO interest rates by credit band. They are examples only, not real offers.
APR_BANDS = {"excellent": 5.0, "good": 6.5, "fair": 9.5, "building": 13.0}
TERM_ADJUST = {36: -0.5, 48: 0.0, 60: 0.5, 72: 1.25}      # longer loans cost a little more per year
MODEL = os.environ.get("ALEX_MODEL", "openai/gpt-oss-20b")
MEMORY_KEYS = {"name", "passengers", "fuel", "budget", "commute", "brand", "era", "use"}

GREETING = ("Hi, I'm Alex, your car expert at Roarwell Motors. I can help you pick a car, explain any spec, "
            "compare models, or work out payments, even make you a deal. What should I call you?")
GREETING_CHIPS = ["Help me choose a car", "Just browsing", "Which cars keep their value best?"]


# ======================================================================
# Tools: plain Python functions the AI can ask us to run
# ======================================================================

def _norm(text):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def resolve_car(query):
    """Find a car from a typed name. Returns (car, None), (None, [candidates]) or (None, [])."""
    q = _norm(query)
    if not q:
        return None, []
    tokens = [t for t in re.findall(r"[a-z0-9]+", str(query).lower()) if t not in ("the", "a", "car")]
    scored = []
    for car in CARS:
        n = _norm(car["name"])
        if q == n:
            score = 1.0
        elif q in n:
            score = 0.6 + 0.4 * len(q) / len(n)
        elif tokens and all(t in n for t in map(_norm, tokens)):
            score = 0.5
        else:
            hit = sum(1 for t in tokens if _norm(t) in n)
            score = 0.4 * hit / len(tokens) if tokens else 0
        if score >= 0.45:
            scored.append((score, car))
    if not scored:
        return None, []
    scored.sort(key=lambda s: -s[0])
    best = scored[0][0]
    top = [c for s, c in scored if s >= best - 0.05]
    if len(top) == 1 or best == 1.0:
        return top[0], None
    return None, top[:6]


def _brief(car):
    return {"name": car["name"], "price": car["price"], "seats": car["seats"], "fuel": car["fuel"],
            "type": car["type"], "mpg": car["mpg"], "keeps_pct_after_5yrs": car["resale_5yr_pct"],
            **({"year": car["year"], "classic": True} if is_vintage(car) else {})}


def _need_car(name):
    car, options = resolve_car(name)
    if car:
        return car, None
    if options:
        return None, {"error": "More than one car matches that name. Ask the customer which one.",
                      "options": [c["name"] for c in options]}
    return None, {"error": f"No car called '{name}' in our lot. Say so honestly, and offer to search for something similar."}


def _append_json(path, record):
    """Keep a simple list of records in a JSON file (our tiny demo 'database')."""
    try:
        items = json.loads(path.read_text()) if path.exists() else []
    except (OSError, json.JSONDecodeError):
        items = []
    items.append(record)
    path.write_text(json.dumps(items, indent=2))


class Toolbox:
    """Everything the agent can do. One instance per customer message."""

    def __init__(self, memory):
        self.memory = memory
        self.ui = []            # things for the website to do (show cars, open one, save one)
        self.cards = []         # cars to show as little photo cards under Alex's reply

    def _cards(self, cars):
        self.cards = [{"id": slugify(c["name"]), "name": c["name"], "price": c["price"],
                       "resale_value": resale_value(c), "resale_pct": c["resale_5yr_pct"]} for c in cars[:6]]

    # --- looking things up ---
    def search_cars(self, max_price=None, min_seats=None, fuel=None, type=None, brand=None, era=None,
                    sort="resale", limit=6):
        cars = list(CARS)
        if max_price:
            cars = [c for c in cars if c["price"] <= float(max_price)]
        if min_seats:
            cars = [c for c in cars if c["seats"] >= int(min_seats)]
        if fuel and fuel not in ("any", "no preference"):
            cars = [c for c in cars if c["fuel"] == str(fuel).lower()]
        if type:
            cars = [c for c in cars if c["type"] == str(type).lower()]
        if brand and brand not in ("any", "no preference"):
            cars = [c for c in cars if c["brand"].lower() == str(brand).lower()]
        if era in ("modern", "classic"):
            cars = [c for c in cars if is_vintage(c) == (era == "classic")]
        keys = {"resale": lambda c: (is_vintage(c), -c["resale_5yr_pct"], c["price"]),
                "price_low": lambda c: c["price"], "price_high": lambda c: -c["price"],
                "mpg": lambda c: -c["mpg"]}
        cars.sort(key=keys.get(sort, keys["resale"]))
        limit = max(1, min(int(limit or 6), 10))
        shown = cars[:limit]
        self._cards(shown)
        out = {"matches_found": len(cars), "showing": [_brief(c) for c in shown]}
        if not cars:
            out["hint"] = "Nothing fits. Suggest loosening the budget, seats, fuel or type."
        return out

    def get_car(self, name):
        car, err = _need_car(name)
        if err:
            return err
        miles = self.memory.get("commute") or 25
        self._cards([car])
        return {**_brief(car), "worth_after_5yrs": resale_value(car),
                "resale_figure_is": "published" if car["resale_source"] == "published" else "a rough estimate",
                "yearly_fuel_cost": yearly_fuel_cost(car, miles), "fuel_cost_based_on_miles_per_day": miles,
                "specs": {label: value for label, value in spec_rows(car)},
                "good_for": profile(car),
                "data_note": "Specs and uses are typical, rounded figures, so tell the customer to confirm details for the exact trim."}

    def compare_cars(self, names):
        found, problems = [], []
        for n in (names or [])[:3]:
            car, err = _need_car(n)
            (found if car else problems).append(car or err)
        if problems:
            return problems[0]
        self._cards(found)
        return {"cars": [{**_brief(c), "worth_after_5yrs": resale_value(c),
                          "yearly_fuel_cost": yearly_fuel_cost(c, self.memory.get("commute") or 25),
                          "towing": profile(c)["towing"], "cargo": profile(c)["cargo"],
                          "drivetrain": spec_rows(c)[7][1], "power": spec_rows(c)[5][1]} for c in found]}

    def estimate_payment(self, name, down_percent=10, years=5, apr=6):
        car, err = _need_car(name)
        if err:
            return err
        loan = car["price"] * (1 - float(down_percent) / 100)
        n = int(years) * 12
        r = float(apr) / 100 / 12
        monthly = loan / n if r == 0 else loan * r / (1 - (1 + r) ** -n)
        return {"car": car["name"], "price": car["price"], "down_payment": round(car["price"] * float(down_percent) / 100),
                "loan_amount": round(loan), "years": int(years), "apr_percent": float(apr),
                "monthly_payment": round(monthly), "total_paid_on_loan": round(monthly * n),
                "note": "An example only. Real rates depend on the buyer's credit and the lender."}


    # --- money talk: payments, price negotiation, closing ---
    def _floor(self, car):
        """The lowest price Alex may ever agree to. Enforced here in Python, never left to the AI."""
        return round(car["price"] * (0.96 if is_vintage(car) else 0.94))

    def _monthly(self, loan, apr, months):
        r = apr / 100 / 12
        return loan / months if r == 0 else loan * r / (1 - (1 + r) ** -months)

    def payment_options(self, name, down_percent=10, credit="good", price=None):
        car, err = _need_car(name)
        if err:
            return err
        credit = str(credit).lower()
        if credit not in APR_BANDS:
            credit = "good"
        deal = (self.memory.get("deal") or {})
        use_price = car["price"]
        if price is not None:                           # only a price Alex really agreed to
            agreed = deal.get("agreed") if deal.get("car") == car["name"] else None
            use_price = min(car["price"], max(float(price), agreed or car["price"]))
        down_percent = max(0.0, min(float(down_percent), 90.0))
        down = round(use_price * down_percent / 100)
        loan = use_price - down
        rows = []
        for months in (36, 48, 60, 72):
            apr = round(APR_BANDS[credit] + TERM_ADJUST[months], 2)
            monthly = self._monthly(loan, apr, months)
            rows.append({"term_months": months, "apr_percent": apr, "monthly_payment": round(monthly),
                         "total_interest": round(monthly * months - loan), "total_paid_on_loan": round(monthly * months)})
        return {"car": car["name"], "price_used": round(use_price), "down_percent": down_percent, "down_payment": down,
                "loan_amount": round(loan), "credit_band": credit, "options": rows,
                "note": "DEMO example rates only, not a real offer. Shorter term = higher monthly payment but less interest. "
                        "Real APR depends on the customer's credit and the lender."}

    def negotiate(self, name, offer):
        car, err = _need_car(name)
        if err:
            return err
        try:
            offer = float(re.sub(r"[^0-9.]", "", str(offer)))
        except ValueError:
            return {"error": "The offer must be a number in dollars."}
        listed, floor = car["price"], self._floor(car)
        deal = self.memory.get("deal") if isinstance(self.memory.get("deal"), dict) else {}
        if deal.get("car") != car["name"] or deal.get("closed"):
            deal = {"car": car["name"], "rounds": 0, "counter": listed, "agreed": None}
        deal["rounds"] = int(deal.get("rounds", 0)) + 1
        counter = float(deal.get("counter", listed))
        step = max(1, round((listed - floor) / 3))
        result = {"car": car["name"], "listed_price": listed, "customer_offer": round(offer), "round": deal["rounds"]}
        if offer >= counter:                                   # we already would have said yes to this
            deal["agreed"] = max(round(counter), floor)      # never charge more than the price we had already offered
            deal["counter"] = deal["agreed"]
            result.update(accepted=True, agreed_price=deal["agreed"],
                          say_to_customer="Accept the offer warmly and move on: ask about down payment and monthly payment, or offer payment_options.")
        elif counter <= floor:                                 # nothing left to give on price
            deal["counter"] = floor
            if offer >= floor:
                deal["agreed"] = round(offer); deal["counter"] = deal["agreed"]
                result.update(accepted=True, agreed_price=deal["agreed"])
            else:
                result.update(accepted=False, counter_price=floor, at_best_price=True,
                              perks_you_may_offer=["a longer or shorter loan term to fit the monthly budget", "a bigger down payment to cut interest",
                                                   "a free demo test drive", "a cheaper car from our lot (use search_cars)"],
                              say_to_customer="This is Alex's best price; do not go lower. Be kind, explain it, and offer the perks or a cheaper car instead.")
        else:
            new_counter = max(floor, round(counter - step))
            # if the offer is close to the new counter, meet it
            if offer >= new_counter:
                deal["agreed"] = round(offer); deal["counter"] = deal["agreed"]
                result.update(accepted=True, agreed_price=deal["agreed"])
            else:
                deal["counter"] = new_counter
                result.update(accepted=False, counter_price=new_counter, at_best_price=(new_counter <= floor),
                              say_to_customer="Counter at counter_price in a friendly way. Say it is demo pricing.")
        self.memory["deal"] = deal
        return result

    def close_deal(self, name, price, term_months=60, apr=None, down_percent=10, confirmed=False):
        car, err = _need_car(name)
        if err:
            return err
        if not confirmed:
            return {"error": "Not confirmed. Summarize the deal (car, price, down payment, term, monthly payment) and ask the customer "
                             "for an explicit yes. Only then call close_deal with confirmed=true."}
        try:
            price = round(float(re.sub(r"[^0-9.]", "", str(price))))
        except ValueError:
            return {"error": "price must be a number."}
        deal = self.memory.get("deal") if isinstance(self.memory.get("deal"), dict) else {}
        floor = self._floor(car)
        lowest = max(floor, deal.get("agreed") or car["price"]) if deal.get("car") == car["name"] else car["price"]
        if price < lowest:
            return {"error": f"That price was not agreed. The agreed price is ${lowest:,}. Use it or negotiate first."}
        price = min(price, car["price"])
        term_months = int(term_months) if int(term_months) in TERM_ADJUST else 60
        apr = float(apr) if apr is not None else APR_BANDS["good"] + TERM_ADJUST[term_months]
        down_percent = max(0.0, min(float(down_percent), 90.0))
        down = round(price * down_percent / 100)
        monthly = round(self._monthly(price - down, apr, term_months))
        record = {"id": "RW-" + "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(5)),
                  "car": car["name"], "car_id": slugify(car["name"]), "price": price, "down_payment": down,
                  "term_months": term_months, "apr_percent": round(apr, 2), "monthly_payment": monthly,
                  "customer": self.memory.get("name") or "Guest", "created": time.strftime("%Y-%m-%d %H:%M"),
                  "demo_only": True}
        _append_json(DEALS_FILE, record)
        deal["closed"] = True
        self.memory["deal"] = deal
        self.ui.append({"type": "deal", "deal": record})
        return {"ok": True, "deal": record, "say_to_customer":
                "Congratulate them! Say this is a demo reservation (no real purchase, no payment taken) and offer to book a test drive."}

    def book_test_drive(self, name, date, time_of_day="10:00"):
        car, err = _need_car(name)
        if err:
            return err
        date, time_of_day = str(date)[:20], str(time_of_day)[:10]
        record = {"id": "TD-" + "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(5)),
                  "car": car["name"], "car_id": slugify(car["name"]), "date": date, "time": time_of_day,
                  "customer": self.memory.get("name") or "Guest", "demo_only": True}
        _append_json(DRIVES_FILE, record)
        self.ui.append({"type": "testdrive", "drive": record})
        return {"ok": True, "booking": record}

    # --- controlling the website ---
    def show_on_page(self, names):
        ids, shown = [], []
        for n in names or []:
            car, _ = resolve_car(n)
            if car:
                ids.append(slugify(car["name"])); shown.append(car["name"])
        if not ids:
            return {"error": "None of those cars were found."}
        self.ui.append({"type": "show", "ids": ids})
        return {"ok": True, "now_showing_on_page": shown}

    def open_car(self, name):
        car, err = _need_car(name)
        if err:
            return err
        self.ui.append({"type": "open", "id": slugify(car["name"])})
        return {"ok": True, "opened": car["name"]}

    def save_car(self, name):
        car, err = _need_car(name)
        if err:
            return err
        self.ui.append({"type": "save", "id": slugify(car["name"])})
        return {"ok": True, "saved_to_shortlist": car["name"]}


TOOLS = {
    "search_cars": "Search our lot. args (all optional): max_price (number), min_seats (number), fuel (petrol|hybrid|diesel|electric), "
                   "type (sedan|hatchback|suv|truck|minivan|coupe), brand, era (modern|classic), sort (resale|price_low|price_high|mpg), limit (1-10)",
    "get_car": "Everything about ONE car: price, specs, resale, fuel cost, and what it is good for (towing, cargo, camping, family, snow). args: name",
    "compare_cars": "Compare 2-3 cars side by side. args: names (list of car names)",
    "estimate_payment": "Monthly loan payment. args: name, down_percent (default 10), years (default 5), apr (default 6)",
    "payment_options": "Loan table for 36/48/60/72 months with demo APRs and total interest. args: name, down_percent (default 10), credit (excellent|good|fair|building, default good), price (optional, only a price Alex agreed to)",
    "negotiate": "Respond to the customer's price offer. The tool decides: accept, counter, or 'best price reached'. NEVER invent a price yourself. args: name, offer (dollars)",
    "close_deal": "Finalize a DEMO reservation after the customer clearly says yes to your summary. args: name, price, term_months (36|48|60|72), apr, down_percent, confirmed (true)",
    "book_test_drive": "Book a test drive. args: name, date (e.g. 2026-11-21 or 'Saturday'), time_of_day (e.g. 10:00)",
    "show_on_page": "Filter the website so it shows only these cars. args: names (list)",
    "open_car": "Open one car's details window on the website. args: name",
    "save_car": "Add one car to the customer's shortlist on the website. args: name",
}


def system_prompt(memory):
    tools = "\n".join(f"- {name}: {desc}" for name, desc in TOOLS.items())
    known = ", ".join(f"{k}={v}" for k, v in memory.items() if v and k != "deal") or "nothing yet"
    return f"""You are Alex, the friendly, honest car expert at Roarwell Motors, a car website. You talk with customers in a warm, relaxed, concise way (usually 2-4 short sentences). You are an AI assistant; never claim to be human.

Our lot has {len(CARS)} cars (modern and classic) from these brands: {', '.join(BRANDS)}.
What you know about this customer so far: {known}.

HOW YOU WORK. You can either use a tool or give your final answer. Write plain text in exactly one of these two shapes.

To use a tool, write ONE line that starts with the word ACTION, then the tool name, then the arguments as JSON:
ACTION get_car {{"name": "Toyota Tacoma"}}

To answer the customer, write REPLY: followed by your message. You may add a CHIPS line (0-4 short ideas for what the customer might tap next, separated by |) and a REMEMBER line (JSON of facts you just learned):
REPLY: Nice to meet you, Bala! Who will usually ride with you?
CHIPS: Just me | 2 people | Family of 4
REMEMBER: {{"name": "Bala"}}

Allowed REMEMBER keys: name, passengers, fuel, budget (number), commute (miles per day, number), brand, era, use (what they need the car for).

TOOLS:
{tools}

RULES
- Facts about our cars (price, seats, specs, resale value, fuel cost, towing, cargo) MUST come from a tool result. Never guess or invent numbers. If a tool did not give the answer, say what you do know and suggest confirming with the maker for the exact trim.
- You may use several tools in a row (for example search_cars, then get_car), then give your final answer.
- If the customer asks for a car we don't carry, say so honestly and offer the closest cars we do have.
- Helping someone choose: learn their needs naturally, ONE question at a time (name, how many people, fuel preference, budget, daily driving, favorite brand, modern or classic, and what they will use it for). You do not need all of them before suggesting cars. Once you know enough, search and recommend 2-3 cars, say why each fits, and offer to compare or show them on the page.
- Resale value is a rough estimate of what the car is worth after 5 years. Classic cars are expected to hold their value but can rise or fall. Do not promise anything about the future or call a car a good investment.
- Do not talk about brand reputation or reliability unless a tool result says it. Do not give legal or financial advice beyond example payments.
- If asked something unrelated to cars or this website, answer briefly and steer back.
- When you use show_on_page, open_car or save_car, tell the customer what you just did on the page.
- DEALS (demo only). You can talk payments, APR, price and close a deal. Be warm, honest, never pushy or pressuring. Prices, APRs, payments and
  counter-offers MUST come from payment_options / negotiate / estimate_payment results. Never quote your own number and never go below a tool's counter_price.
- If the customer's budget is tight: suggest a longer term, a bigger down payment, or a cheaper car, and explain that longer terms cost more interest.
- When a customer offers a price, call negotiate. If it says at_best_price, kindly explain you can't go lower, then offer perks (term, down payment, test drive) or alternatives. Be lenient and friendly, but the tool decides.
- Never ask for card numbers, bank details, SSN, or ID. This is a demo reservation: no real purchase, no payment taken, and example rates are not real offers. You are not a financial advisor.
- To close: first summarize car, price, down payment, term, APR and monthly payment and ask "Shall I lock it in?". Only after a clear yes call close_deal with confirmed=true. Then congratulate and offer a test drive (book_test_drive needs a date).
- Always start your message with either ACTION or REPLY:. Never write anything before it."""


# ======================================================================
# The agent loop
# ======================================================================

def _json_after(text):
    """Parse the first {...} in text, or return {}."""
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(text[start:end + 1])
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            pass
    return {}


def parse_model_output(text):
    """Turn the AI's text into {"tool", "args"} or {"say", "chips", "remember"}.
    Understands our ACTION/REPLY lines, and also JSON (in case the AI uses that instead)."""
    raw = str(text or "").strip()
    raw = re.sub(r"^```[a-z]*\s*|\s*```$", "", raw).strip()

    action = re.search(r"^\s*ACTION[: ]+\s*([A-Za-z_]+)\s*(.*)$", raw, re.MULTILINE | re.DOTALL)
    if action and "REPLY:" not in raw[:action.start()]:
        return {"tool": action.group(1), "args": _json_after(action.group(2).split("\n")[0]) or _json_after(action.group(2))}

    reply = re.search(r"^\s*REPLY:\s*(.*)\Z", raw, re.MULTILINE | re.DOTALL)
    if reply:
        body = reply.group(1)
        # CHIPS: and REMEMBER: may sit on their own line OR glued to the end of the sentence, so look for them anywhere
        marker = re.compile(r"(?:(?<=\s)|(?<=[.?!)\"']))(CHIPS|REMEMBER):\s*")
        first = marker.search(body)
        say = body[:first.start()] if first else body
        say = re.split(r"\s*REPLY:\s*", say.strip())[0].strip() or say.strip()     # the AI sometimes repeats itself
        out = {"say": say}
        for m in marker.finditer(body):
            rest = body[m.end():]
            nxt = marker.search(rest)
            piece = (rest[:nxt.start()] if nxt else rest).strip()
            if m.group(1) == "CHIPS":
                piece = piece.split("\n")[0]
                out["chips"] = [c.strip() for c in piece.split("|") if c.strip()]
            else:
                out["remember"] = _json_after(piece)
        return out

    data = _json_after(raw)                           # the AI used JSON instead
    for _ in range(3):                                # unwrap function-call style answers
        if "tool" in data or "say" in data:
            return data
        args = data.get("arguments", data.get("args", data.get("parameters")))
        if isinstance(args, str):
            args = _json_after(args)
        name = data.get("name") or data.get("function")
        if name in TOOLS and isinstance(args, dict):  # {"name": "search_cars", "arguments": {...}}
            return {"tool": name, "args": args}
        if isinstance(args, dict) and args:           # {"name": "assistant", "arguments": {...real answer...}}
            data = args
            continue
        break
    if raw.lstrip().startswith(("{", "[")):           # never show raw code to a customer; "_bad" makes the agent ask again
        return {"say": "Sorry, I got tangled up for a second. Could you say that again?", "_bad": True}
    return {"say": raw or "Sorry, could you say that again?"}      # plain speech


def _rescue(text):
    """Pull the rejected answer out of a Groq 400 error message."""
    m = re.search(r"'failed_generation': '(.*)'\}\}?\s*$", text, re.DOTALL) or re.search(r"failed_generation['\"]?: ['\"](.*)", text, re.DOTALL)
    if not m:
        return None
    return m.group(1).replace("\\\"", '"').replace("\\n", "\n").replace("\\'", "'")


NUDGE = ("Your last answer could not be read. Answer again now, in exactly one of these two shapes, and write no reasoning "
         "or explanation: either one line starting with ACTION <tool> {json}, or REPLY: <message to the customer>.")


def call_model(llm, messages):
    """Ask the AI. Groq sometimes rejects an answer ('tool_use_failed' or 'output_parse_failed', for example when the
    model starts 'thinking out loud'). The rejected text is still inside the error, so we rescue it if it looks like
    an ACTION or REPLY, otherwise we ask again with a firm reminder. After 3 tries Alex asks the customer to rephrase."""
    from langchain_core.messages import HumanMessage
    messages = list(messages)
    for attempt in range(3):
        try:
            if _BUSY.get(getattr(llm, "model_name", None), 0) > time.time():
                raise RuntimeError("429 rate limit (this model was busy a moment ago)")   # skip straight to a backup
            return llm.invoke(messages).content
        except Exception as problem:
            text = str(problem)
            if _is_rate_limit(text):                    # this model's free allowance is used up: try the next one
                _BUSY[getattr(llm, "model_name", None)] = time.time() + 300
                for spec in available_fallbacks():
                    name = model_id(spec)
                    if name == getattr(llm, "model_name", None) or _BUSY.get(name, 0) > time.time():
                        continue
                    try:
                        if DEBUG:
                            print(f"[alex] rate limit hit, switching to {spec}")
                        return make_llm(spec).invoke(messages).content
                    except Exception as again:
                        if _is_rate_limit(str(again)):
                            _BUSY[name] = time.time() + 300
                        elif DEBUG:
                            print(f"[alex] {spec} failed: {str(again)[:150]}")
                        continue
                raise
            if "tool_use_failed" not in text and "output_parse_failed" not in text and "failed_generation" not in text:
                raise                                   # a real problem (key, network...): let the website explain it
            rescued = _rescue(text)
            if rescued and re.search(r"(^|\n)\s*(ACTION|REPLY:)", rescued) or (rescued and rescued.lstrip().startswith("{")):
                return rescued
            messages.append(HumanMessage(content=NUDGE))
    return "REPLY: Sorry, I lost my train of thought for a second. Could you say that another way?"


def clean_memory(update):
    out = {}
    if not isinstance(update, dict):
        return out
    for key, value in update.items():
        if key not in MEMORY_KEYS or value in (None, "", [], {}):
            continue
        if key in ("budget", "commute", "passengers"):
            try:
                out[key] = int(float(re.sub(r"[^0-9.]", "", str(value))))
            except ValueError:
                continue
        else:
            out[key] = str(value).strip()[:60]
    return out


# A "spec" names a model and where it lives:  "openai/gpt-oss-20b" (Groq),  "cerebras:gpt-oss-120b",  "openrouter:openai/gpt-oss-20b:free"
PROVIDERS = {
    "cerebras": ("CEREBRAS_API_KEY", "https://api.cerebras.ai/v1"),
    "openrouter": ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1"),
}


def model_id(spec):
    """The plain model name inside a spec ('cerebras:gpt-oss-120b' -> 'gpt-oss-120b')."""
    head, _, rest = spec.partition(":")
    return rest if head in PROVIDERS else spec


def make_llm(spec):
    """Build the AI for one spec: Groq by default, or Cerebras / OpenRouter (both speak the OpenAI chat format)."""
    head, _, rest = spec.partition(":")
    if head in PROVIDERS:
        from langchain_openai import ChatOpenAI
        key_name, url = PROVIDERS[head]
        return ChatOpenAI(model=rest, api_key=os.environ.get(key_name, ""), base_url=url,
                          temperature=0.3, timeout=30, max_retries=1)
    from langchain_groq import ChatGroq
    kwargs = {"model": spec, "temperature": 0.3, "timeout": 30, "max_retries": 1}
    effort = os.environ.get("ALEX_REASONING", "").strip().lower()      # low | medium | high: lower = faster replies
    if effort in ("low", "medium", "high") and spec.startswith("openai/gpt-oss"):
        kwargs["model_kwargs"] = {"reasoning_effort": effort}
    return ChatGroq(**kwargs)


# Every free model has its OWN daily allowance. When one runs out (error 429), Alex quietly switches to the next
# one in this list instead of failing: other Groq models first, then Cerebras, then OpenRouter.
# A provider is only used if its key is in .env. Change the list with ALEX_FALLBACKS (comma separated specs).
def fallback_specs():
    """The backup list, read when needed (so values from .env are already loaded)."""
    default = ",".join([
        "openai/gpt-oss-120b", "llama-3.1-8b-instant",
        "cerebras:" + os.environ.get("CEREBRAS_MODEL", "gpt-oss-120b"),
        "openrouter:" + os.environ.get("OPENROUTER_MODEL", "openai/gpt-oss-20b:free"),
    ])
    return [m.strip() for m in os.environ.get("ALEX_FALLBACKS", default).split(",") if m.strip()]


_BUSY = {}      # model name -> time until which we skip it (it said "rate limit")


def has_key(spec):
    head = spec.partition(":")[0]
    return bool(os.environ.get(PROVIDERS[head][0] if head in PROVIDERS else "GROQ_API_KEY"))


def available_fallbacks():
    """Backups whose API key is set, so we never try a provider we have no key for."""
    return [m for m in fallback_specs() if has_key(m)]


def _is_rate_limit(text):
    low = text.lower()
    return "429" in text or "rate limit" in low or "RateLimitError" in text or "too many requests" in low or "queue_exceeded" in low


def get_llm():
    """Create the AI the first time it is needed (the main Groq model, or a backup if there is no Groq key)."""
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
    if has_key(MODEL):
        return make_llm(MODEL)
    for spec in available_fallbacks():
        return make_llm(spec)
    raise RuntimeError("No AI key found. Put a line like GROQ_API_KEY=gsk_... in the .env file next to server.py.")


# ----------------------------------------------------------------------
# The agent loop as a LANGGRAPH graph
#
#        START --> [call_model] --(wants a tool)--> [run_tool] --+
#                      ^                                         |
#                      +-----------------------------------------+
#                      |
#                      +--(has a final answer)--> END
#
# Each box is a "node" (a small Python function). The arrow after call_model is a "conditional edge": a function
# looks at the state and chooses where to go next. The shared "state" carries the conversation, the tool steps
# and the final answer from node to node.
# ----------------------------------------------------------------------
from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    llm: Any              # the AI
    messages: list        # conversation sent to the AI
    tools: Any            # the Toolbox for this customer message
    steps: list           # tools used so far
    pending: dict         # the tool the AI just asked for
    final: dict           # the AI's final answer
    turns: int            # how many times we asked the AI (a safety limit)


def call_model_node(state):
    """Ask the AI what to do next and read its answer. Unreadable answers are retried, then answered in plain text."""
    from langchain_core.messages import HumanMessage
    messages = state["messages"]
    if state.get("turns", 0) >= MAX_TOOL_STEPS + 3:      # safety net: never loop forever
        return {"final": {"say": "Sorry, I got a bit tangled up there. Could you ask me that another way?"}}
    data = {}
    for attempt in range(3):
        started = time.time()
        raw = call_model(state["llm"], messages)
        data = parse_model_output(raw)
        if DEBUG:
            print(f"[alex] attempt {attempt + 1} took {time.time() - started:.1f}s, raw model output: {str(raw)[:400]!r}")
        if not data.get("_bad"):
            break
        messages = messages + [HumanMessage(content=NUDGE)]
    else:                                                  # still unreadable: ask for a plain-text answer instead
        plain = call_model(state["llm"], messages + [HumanMessage(content=(
            "Forget the special format. Just answer the customer's last message in 1-3 friendly plain sentences. No JSON, no code."))])
        plain = re.sub(r"^\s*REPLY:\s*", "", str(plain)).strip()
        data = {"say": plain if plain and not plain.startswith(("{", "[")) else "Sorry, could you say that another way?"}
    data.pop("_bad", None)
    if "tool" in data and len(state["steps"]) >= MAX_TOOL_STEPS:    # too many tool calls: demand an answer
        return {"messages": messages + [HumanMessage(content="Stop using tools. Give your final answer now, starting with REPLY:.")],
                "turns": state.get("turns", 0) + 1, "pending": {}}
    if "tool" in data:
        return {"pending": data, "messages": messages, "turns": state.get("turns", 0) + 1}
    return {"final": data, "pending": {}}


def run_tool_node(state):
    """Run the tool the AI asked for (plain Python) and hand the result back to the AI."""
    from langchain_core.messages import AIMessage, HumanMessage
    data, tools = state["pending"], state["tools"]
    name, args = str(data["tool"]), data.get("args") or {}
    fn = getattr(tools, name, None) if name in TOOLS else None
    try:
        result = fn(**args) if fn else {"error": f"There is no tool called '{name}'. Available: {', '.join(TOOLS)}"}
    except Exception as problem:                      # bad arguments from the AI: tell it, let it retry
        result = {"error": f"Tool failed: {problem}. Check the args and try again."}
    messages = state["messages"] + [
        AIMessage(content=f"ACTION {name} {json.dumps(args)}"),
        HumanMessage(content="TOOL RESULT: " + json.dumps(result)[:3500]
                     + "\nNow continue: write another ACTION line, or give your final answer starting with REPLY:.")]
    return {"messages": messages, "steps": state["steps"] + [{"tool": name, "args": args}], "pending": {}}


def after_model(state):
    """The conditional edge: tool requested -> run it; otherwise -> loop (if told to answer) or finish."""
    if state.get("final"):
        return "done"
    return "tool" if state.get("pending") else "again"


def build_graph():
    from langgraph.graph import StateGraph, START, END
    g = StateGraph(AgentState)
    g.add_node("call_model", call_model_node)
    g.add_node("run_tool", run_tool_node)
    g.add_edge(START, "call_model")
    g.add_conditional_edges("call_model", after_model, {"tool": "run_tool", "again": "call_model", "done": END})
    g.add_edge("run_tool", "call_model")
    return g.compile()


_GRAPH = None


def run_agent(llm, user_text, history, memory):
    """One customer message in, Alex's reply out. `history` is a list of {"role": "user"|"alex", "text": ...}."""
    global _GRAPH
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    memory = dict(memory or {})
    tools = Toolbox(memory)
    messages = [SystemMessage(content=system_prompt(memory))]
    for turn in (history or [])[-6:]:
        text = str(turn.get("text", ""))[:1500]
        messages.append(HumanMessage(content=text) if turn.get("role") == "user" else AIMessage(content="REPLY: " + text))
    messages.append(HumanMessage(content=str(user_text)[:1500]))

    _GRAPH = _GRAPH or build_graph()
    state = _GRAPH.invoke({"messages": messages, "tools": tools, "llm": llm, "steps": [], "pending": {}, "turns": 0},
                          {"recursion_limit": 40})
    steps = state.get("steps", [])
    final = state.get("final") or {"say": "Sorry, I got a bit tangled up there. Could you ask me that another way?"}
    memory.update(clean_memory(final.get("remember")))
    chips = [str(c)[:40] for c in (final.get("chips") or []) if c][:4] if isinstance(final.get("chips"), list) else []
    return {"reply": str(final.get("say", "")).strip() or "Could you say that again?",
            "chips": chips, "memory": memory, "ui": tools.ui, "cards": tools.cards, "steps": steps}
