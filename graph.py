"""graph.py - the BRAIN of Alex, the car buyer agent.

The flow (each box is a LangGraph "node"):

    START -> (answering "choosing this car?") -> decision -> END
          -> (customer named a specific car?) -> detail -> END
          -> extract -> do we know everything? -+-> no  -> ask       -> END
                                                |
                                                +-> yes -> recommend -> END
                                                |         (or clarify -> END, when a
                                                |          message changed nothing)

Each time the user types a message, the graph runs once.
"""
import json
import re
from typing import Optional, TypedDict

from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END

from cars import CARS, BRANDS, is_vintage, resale_value, yearly_fuel_cost
from specs import spec_rows

load_dotenv()
llm = ChatGroq(model="openai/gpt-oss-20b")


# ---------- 1. The shape of our data ----------

class Preferences(BaseModel):
    """What we want the LLM to pull out of the user's message."""
    name: Optional[str] = None
    passengers: Optional[int] = None
    fuel: Optional[str] = None
    budget: Optional[int] = None
    commute: Optional[int] = None     # miles driven per day
    brand: Optional[str] = None       # a brand name, or "any"
    era: Optional[str] = None         # "modern", "classic" or "either"
    car_type: Optional[str] = None    # optional: we never ask, but we use it if offered


class State(TypedDict):
    """The shared notebook that every node can read and write."""
    user_text: str       # what the user just typed
    last_question: str   # the question Alex last asked
    prefs: dict          # everything we've learned so far
    reply: str           # what Alex says back
    matches: list        # recommended cars (for the cards in the UI later)
    choices: list        # car names we offered when asking 'which one do you mean?'
    pending_car: str     # the car we just described, while we wait for 'choosing it?'
    specs: list          # spec sheet rows (label, value) for the chosen car
    learned: bool        # did the customer's message tell us anything new?


# The questions, in the order Alex asks them.
QUESTIONS = {
    "name": "Hi, I'm Alex! 👋 What should I call you?",
    "passengers": "How many people will usually ride in the car, including you?",
    "fuel": "Which fuel do you prefer: petrol, diesel, electric or hybrid? (or say 'no preference')",
    "budget": "What's your budget in dollars?",
    "commute": "About how many miles do you drive per day, on average?",
    "brand": "Do you have a favorite brand in mind? (or say 'no preference')",
    "era": "Are you looking for a modern car, a classic (vintage) car, or either?",
}


# After recommendations (or a "no match"), the customer is probably changing an answer.
# We pass this to the AI so it knows how to read short replies like "60000" or "either".
CHANGE_CONTEXT = ("I just showed my results. The customer may now be changing one of their "
                  "answers: passengers, fuel, budget, commute, brand or era.")


def missing_field(prefs):
    """Return the first thing we still don't know, or None."""
    for key in QUESTIONS:
        if prefs.get(key) is None:
            return key
    return None


# ---------- 2. The nodes (the steps) ----------

def parse_preferences(raw):
    """Turn the AI's JSON text into a dict of preferences.

    The AI sometimes wraps its JSON in a ```json code block or adds a sentence
    around it, so we cut out just the part between the first { and the last }.
    If anything looks wrong we return {} (= "learned nothing new") instead of crashing.
    """
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        return {}
    try:
        data = json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return {}

    # Numbers sometimes arrive as text like "$40,000", "40k" or "30 miles".
    for key in ("passengers", "budget", "commute"):
        value = data.get(key)
        if isinstance(value, str):
            match = re.search(r"(\d+(?:\.\d+)?)\s*(k)?", value.lower().replace(",", ""))
            data[key] = int(float(match.group(1)) * (1000 if match.group(2) else 1)) if match else None

    try:
        return Preferences(**data).model_dump()
    except Exception:
        return {}


def extract_node(state: State):
    """Use the LLM to read the user's message and pull out preferences."""
    prompt = f"""Extract car-buying preferences from the user's message.
Only fill in what the user actually said. Leave everything else null.

- name: only if the user is telling us their own name or what to call them.
- passengers: number of people who will ride in the car.
- fuel: one of petrol, diesel, electric, hybrid. Use "any" if they have no preference.
- budget: a number in dollars, like 30000.
- commute: miles driven per day, as a number. If they say they don't know, use 20.
- brand: the car brand as a plain name like "Toyota". Use "any" if they have no preference.
- era: "modern" for new cars, "classic" for vintage/old/antique cars, "either" if they don't mind.
- car_type: one of sedan, suv, hatchback, truck, minivan, coupe. Only if they say it.

If the user types only a number and the question above doesn't say what it is:
a number under 15 means passengers, and a number of 1000 or more means budget.

The assistant just asked: "{state['last_question']}"
User's message: "{state['user_text']}"

Reply with ONLY a JSON object with exactly these keys:
name, passengers, fuel, budget, commute, brand, era, car_type
Use null for anything the user did not mention. No explanation and no code fences."""
    found = parse_preferences(llm.invoke(prompt).content)

    # Merge new info into what we already knew
    prefs = dict(state["prefs"])
    for key, value in found.items():
        if value is None:
            continue
        if key == "name" and prefs.get("name"):
            continue  # never overwrite a name we already have
        prefs[key] = value
    return {"prefs": prefs, "learned": any(v is not None for v in found.values())}


def ask_node(state: State):
    """Ask the next question we still need answered."""
    prefs = state["prefs"]
    question = QUESTIONS[missing_field(prefs)]
    reply = question
    # Right after we learn their name, say hello properly.
    if state["last_question"] == QUESTIONS["name"] and prefs.get("name"):
        reply = f"Nice to meet you, {prefs['name']}! {question}"
    return {"reply": reply, "last_question": question, "matches": [], "choices": [], "pending_car": ""}


def fits(car, p):
    """Does this car match what the customer told us?"""
    if car["price"] > p["budget"]:
        return False
    if car["seats"] < p["passengers"]:
        return False
    if str(p["fuel"]).lower() != "any" and car["fuel"] != str(p["fuel"]).lower():
        return False
    if p.get("car_type") and car["type"] != str(p["car_type"]).lower():
        return False
    era = str(p["era"]).lower()
    if is_vintage(car):
        return era in ("classic", "either")
    return era in ("modern", "either")


def count_fits(p, **changes):
    """How many cars would fit if we changed some of the customer's answers?"""
    return sum(fits(c, dict(p, **changes)) for c in CARS)


def explain_no_match(p):
    """Find which single answer is blocking us, by relaxing them one at a time."""
    ideas = []

    if str(p["era"]).lower() != "either" and count_fits(p, era="either"):
        ideas.append("include both modern and classic cars (say 'either')")

    if p["passengers"] > 1:
        options = [c for c in CARS if fits(c, dict(p, passengers=0))]
        if options:
            best_seats = max(c["seats"] for c in options)
            ideas.append(f"fewer than {p['passengers']} passengers "
                         f"(the best match seats {best_seats})")

    options = [c for c in CARS if fits(c, dict(p, budget=10**9))]
    if options:
        ideas.append(f"a bigger budget (the cheapest match costs ${min(c['price'] for c in options):,})")

    if str(p["fuel"]).lower() != "any" and count_fits(p, fuel="any"):
        ideas.append("a different fuel type (say 'no preference')")

    if p.get("car_type") and count_fits(p, car_type=None):
        ideas.append("dropping the car type")

    return ideas


# Words that name a question, so a bare "budget" can be answered by asking that question.
FIELD_WORDS = {
    "budget": "budget", "price": "budget", "cost": "budget", "money": "budget",
    "passengers": "passengers", "people": "passengers", "seats": "passengers", "family": "passengers",
    "fuel": "fuel", "commute": "commute", "miles": "commute", "drive": "commute",
    "brand": "brand", "make": "brand", "era": "era",
}


def clarify_node(state: State):
    """The customer said something but we couldn't find a change in it."""
    for word in tokens(state["user_text"]):
        if word in FIELD_WORDS:
            question = QUESTIONS[FIELD_WORDS[word]]
            return {"reply": question, "last_question": question, "matches": [], "choices": [],
                    "pending_car": ""}
    reply = ("I didn't catch what you'd like to change. You can say things like "
             "'budget 60000', 'hybrid', 'toyota', or 'classic', or type a car's name.")
    return {"reply": reply, "last_question": CHANGE_CONTEXT, "matches": [], "choices": [],
            "pending_car": ""}


def more_options_note(p, current):
    """When very few cars fit, say what would open up more."""
    ideas = []
    if str(p["fuel"]).lower() != "any":
        more = count_fits(p, fuel="any") - current
        if more > 0:
            ideas.append(f"a different fuel type, say 'no preference' ({more} more)")
    if str(p["era"]).lower() != "either":
        more = count_fits(p, era="either") - current
        if more > 0:
            ideas.append(f"both modern and classic cars, say 'either' ({more} more)")
    bigger = int(p["budget"] * 1.5)
    more = count_fits(p, budget=bigger) - current
    if more > 0:
        ideas.append(f"a budget up to ${bigger:,} ({more} more)")
    if not ideas:
        return ""
    noun = "car fits" if current == 1 else "cars fit"
    return f"Only {current} {noun} everything you asked for. To see more, you could try:\n" + \
        "\n".join(f"  - {i}" for i in ideas)


def recommend_node(state: State):
    """Filter the car list, show favorite-brand cars first, then other options."""
    p = state["prefs"]
    brand = str(p["brand"]).lower()
    known_brands = [b.lower() for b in BRANDS]
    wants_brand = brand != "any"

    # Sort: modern cars before classics, then best resale value first.
    def sort_key(car):
        return (is_vintage(car), -car["resale_5yr_pct"], car["price"])

    fitting = sorted((c for c in CARS if fits(c, p)), key=sort_key)
    brand_group = [c for c in fitting if wants_brand and c["brand"].lower() == brand][:5]
    other_group = [c for c in fitting if c not in brand_group][:5]

    # Add the calculated facts to copies of the cars.
    matches = []
    other_label = "other" if wants_brand else "top"      # no favorite brand -> "top picks"
    for group, cars in (("brand", brand_group), (other_label, other_group)):
        for car in cars:
            matches.append(dict(
                car,
                group=group,
                resale_value=resale_value(car),
                fuel_cost=yearly_fuel_cost(car, p["commute"]),
            ))

    name = p["name"]
    if not matches:
        ideas = explain_no_match(p)
        reply = f"Sorry {name}, I couldn't find a car that fits all of that."
        if ideas:
            reply += " Any one of these would open up options:\n" + "\n".join(f"  - {i}" for i in ideas)
        else:
            reply += " Try changing two or more things, like the budget and the seats."
        reply += "\nJust tell me what to change, for example 'either' or 'budget 60000'."
        return {"reply": reply, "last_question": CHANGE_CONTEXT, "matches": [], "choices": [], "pending_car": ""}

    lines = []
    for m in matches:
        lines.append(
            f"- [{m['group']}] {m['name']}: ${m['price']:,}, {m['seats']} seats, {m['fuel']}, "
            f"keeps about {m['resale_5yr_pct']}% after 5 years (about ${m['resale_value']:,}, "
            f"{m['resale_source']}), fuel about ${m['fuel_cost']:,}/year, "
            f"{'CLASSIC' if is_vintage(m) else 'modern'}"
        )

    brand_note = ""
    if wants_brand and brand not in known_brands:
        brand_note = f"We don't carry {p['brand']}, so say so briefly and show the other options."
    elif wants_brand and not brand_group:
        brand_note = f"No {p['brand']} fits their budget and needs, so say so briefly."

    prompt = f"""You are Alex, a friendly car salesperson. Customer name: {name}.
They want: {p}
{brand_note}

Recommend ONLY from this list (never invent cars or numbers):
{chr(10).join(lines)}

Write a SHORT reply of 3 to 5 sentences. The full list of cars is shown to the customer
separately, so do NOT list every car again.
1. Do not start with a greeting. You may use their name once.
2. Say that the [brand] cars come first (their favorite brand) and the [other] cars are
   alternatives in the same price range. Skip this if there is only one group. Cars tagged
   [top] are simply our top picks for them.
3. Name the best pick for resale value and why. If several cars tie on resale (like classics
   at 100%), say they are tied instead of picking one.
4. Resale figures marked "estimate" are rough estimates, so call them estimates.
5. Classic cars are collectibles: their value can go up or down. Never call a car a good
   investment and never promise returns.
6. Use ONLY the facts in the list. Do not praise a brand's reputation or reliability, and do
   not mention features that are not listed.
7. End by saying they can type a car's name for details, or change any answer (like 'budget 60000')."""
    reply = llm.invoke(prompt).content
    if len(fitting) < 3:
        note = more_options_note(p, len(fitting))
        if note:
            reply += "\n\n" + note
    return {"reply": reply, "last_question": CHANGE_CONTEXT, "matches": matches, "choices": [], "pending_car": ""}


# ---------- Looking up a specific car ----------

def tokens(text):
    """Split text into lowercase words and numbers: 'CR-V 2024' -> ['cr', 'v', '2024']."""
    return re.findall(r"[a-z0-9]+", text.lower())


# Words that describe a kind of car, not a specific model.
GENERIC_WORDS = {"hybrid", "electric", "petrol", "diesel", "suv", "sedan", "hatchback",
                 "truck", "minivan", "coupe", "classic", "vintage", "modern", "either"}


FUEL_WORDS = {"petrol", "diesel", "electric", "hybrid"}
TYPE_WORDS = {"suv", "sedan", "hatchback", "truck", "minivan", "coupe"}


def lookup_cars(text):
    """Did the customer type the name of a specific car? Returns the matching cars.

    Works with full names ("Honda CR-V Hybrid"), short names ("camry", "civic") and
    short searches like "toyota hybrid" or "ford truck" (a brand plus a fuel or body type).
    """
    brand_words = {b.lower() for b in BRANDS}
    vocabulary = {t for car in CARS for t in tokens(car["name"])}
    typed = set(tokens(text))
    named_brands = typed & brand_words

    wanted = (typed & vocabulary) - brand_words - GENERIC_WORDS
    # Need a real word like 'camry' or 'rav4', or a number with 3+ digits like '1969' or
    # '150'. A short lone number is an answer like "4 passengers", not a car name.
    if any((any(ch.isalpha() for ch in t) and len(t) > 1) or len(t) >= 3 for t in wanted):
        candidates = [
            car for car in CARS
            if wanted <= set(tokens(car["name"]))
            and (not named_brands or car["brand"].lower() in named_brands)
        ]
        # If the customer typed a car's COMPLETE name, that exact car wins. Without this,
        # "Honda CR-V Hybrid" would also match plain "Honda CR-V" and we'd ask again forever.
        typed_full_name = [car for car in candidates if set(tokens(car["name"])) <= typed]
        if typed_full_name:
            longest = max(len(tokens(car["name"])) for car in typed_full_name)
            return [car for car in typed_full_name if len(tokens(car["name"])) == longest]
        return candidates

    # Short search: a brand plus a fuel or body type, like "toyota hybrid" or "ford truck".
    # (A brand alone or "hybrid" alone is NOT a car name: that is the customer changing an answer.)
    fuels, types = typed & FUEL_WORDS, typed & TYPE_WORDS
    if named_brands and (fuels or types):
        return [
            car for car in CARS
            if car["brand"].lower() in named_brands
            and (not fuels or car["fuel"] in fuels)
            and (not types or car["type"] in types)
        ]
    return []


def pick_from_choices(text, choices):
    """The customer answered our 'which one do you mean?' with a number or a short name."""
    answer = text.strip()
    if answer.isdigit() and 1 <= int(answer) <= len(choices):
        return [car for car in CARS if car["name"] == choices[int(answer) - 1]]
    found = [car for car in lookup_cars(text) if car["name"] in choices]
    return found if len(found) == 1 else []


def detail_node(state: State):
    """The customer named a car: tell them about it, and how it fits their answers."""
    p = state["prefs"]
    choices = state.get("choices", [])
    cars = pick_from_choices(state["user_text"], choices) if choices else []
    if not cars:
        cars = lookup_cars(state["user_text"])

    if len(cars) > 8:
        reply = "I have quite a few like that. Could you narrow it down, like 'toyota suv'?"
        return {"reply": reply, "last_question": CHANGE_CONTEXT, "matches": [], "choices": [], "pending_car": ""}
    if len(cars) > 1:
        lines = [f"  {number}. {c['name']}  (${c['price']:,}, {c['fuel']} {c['type']})"
                 for number, c in enumerate(cars, start=1)]
        reply = ("Which one do you mean?\n" + "\n".join(lines)
                 + "\nType the number or the name.")
        return {"reply": reply, "last_question": CHANGE_CONTEXT, "matches": [],
                "choices": [c["name"] for c in cars], "pending_car": ""}

    car = cars[0]
    notes = []
    if car["price"] > p["budget"]:
        notes.append(f"It costs ${car['price'] - p['budget']:,} more than their ${p['budget']:,} budget.")
    if car["seats"] < p["passengers"]:
        notes.append(f"It seats only {car['seats']} and they need {p['passengers']}.")
    if str(p["fuel"]).lower() not in ("any", car["fuel"]):
        notes.append(f"It runs on {car['fuel']}, not their preferred {p['fuel']}.")
    if not notes:
        notes.append("It fits all of their answers.")

    card = dict(car, group="chosen", resale_value=resale_value(car),
                fuel_cost=yearly_fuel_cost(car, p["commute"]))
    facts = (f"{car['name']}: ${car['price']:,}, {car['seats']} seats, {car['fuel']}, "
             f"{car['type']}, keeps about {car['resale_5yr_pct']}% after 5 years "
             f"(about ${card['resale_value']:,}, {car['resale_source']}), "
             f"fuel about ${card['fuel_cost']:,}/year, "
             f"{'CLASSIC collectible' if is_vintage(car) else 'modern'}")
    prompt = f"""You are Alex, a friendly car salesperson talking to {p['name']}.
They asked about this car. Use ONLY these facts, never add other details:
{facts}
How it fits them: {' '.join(notes)}

Write 2 to 4 short sentences. No greeting. Say how it fits them. Resale marked "estimate"
is a rough estimate. If it is a classic, its value can go up or down; never call it an
investment or promise returns."""
    reply = llm.invoke(prompt).content
    if car["price"] > p["budget"]:
        reply += f"\nSay 'budget {car['price']}' and I'll include it in your results."
    reply += f"\n\n{DECISION_QUESTION}"
    return {"reply": reply, "last_question": CHANGE_CONTEXT, "matches": [card], "choices": [],
            "pending_car": car["name"]}


# ---------- "Are you choosing this car?" ----------

DECISION_QUESTION = "Are you choosing this car, or still looking at other models?"
TAGLINE = "Let's go for a spin! 🏁"

# Words that tell us the customer is still browsing / has chosen. Browsing is checked first,
# so "not choosing yet" counts as browsing.
BROWSE_WORDS = {"looking", "other", "others", "models", "compare", "comparing", "more", "still",
                "not", "no", "nope", "browse", "browsing", "options", "show", "else", "different"}
CHOOSE_WORDS = {"choosing", "choose", "chose", "buy", "buying", "take", "taking", "yes", "yeah",
                "yep", "yup", "sure", "definitely", "ok", "okay", "spin"}


def choice_intent(text):
    """Is the customer choosing the car ('choose'), still browsing ('browse'), or neither (None)?"""
    words = set(tokens(text))
    if words & BROWSE_WORDS:
        return "browse"
    if words & CHOOSE_WORDS:
        return "choose"
    return None


def decision_node(state: State):
    """The customer answered 'choosing this car?': show the spec sheet, or keep browsing."""
    p = state["prefs"]
    car = next(c for c in CARS if c["name"] == state["pending_car"])

    if choice_intent(state["user_text"]) == "choose":
        reply = (f"Great choice, {p['name']}! Here is the full spec sheet for the {car['name']}. "
                 "(These are typical base-trim figures, rounded. They vary by year and trim.)")
        specs = spec_rows(car)
    else:
        reply = (f"No problem, {p['name']}, take your time! Type another car's name, "
                 "or change an answer (like 'budget 60000').")
        specs = []
    return {"reply": reply, "last_question": CHANGE_CONTEXT, "matches": [], "choices": [],
            "pending_car": "", "specs": specs}


# ---------- 3. The fork in the road ----------

def route_start(state: State):
    """First fork: once we know everything, a car name means 'tell me about that car'."""
    if state.get("pending_car") and choice_intent(state["user_text"]):
        return "decision"
    if missing_field(state["prefs"]) is None:
        choices = state.get("choices", [])
        if (choices and pick_from_choices(state["user_text"], choices)) or lookup_cars(state["user_text"]):
            return "detail"
    return "extract"


def route(state: State):
    """Conditional edge: what happens after we read the customer's message?"""
    if missing_field(state["prefs"]):
        return "ask"
    # Results are already on screen and this message changed nothing: ask what they meant.
    if state["last_question"] == CHANGE_CONTEXT and not state.get("learned", True):
        return "clarify"
    return "recommend"


# ---------- 4. Wire the graph together ----------

builder = StateGraph(State)
builder.add_node("extract", extract_node)
builder.add_node("ask", ask_node)
builder.add_node("recommend", recommend_node)
builder.add_node("detail", detail_node)
builder.add_node("decision", decision_node)
builder.add_node("clarify", clarify_node)

builder.add_conditional_edges(START, route_start, {"detail": "detail", "decision": "decision", "extract": "extract"})
builder.add_conditional_edges("extract", route, {"ask": "ask", "recommend": "recommend", "clarify": "clarify"})
builder.add_edge("ask", END)
builder.add_edge("recommend", END)
builder.add_edge("detail", END)
builder.add_edge("decision", END)
builder.add_edge("clarify", END)

graph = builder.compile()