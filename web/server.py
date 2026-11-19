"""server.py - the web server for the Roarwell Motors website.

It does two jobs:
  1. Serves the website files in the web/ folder (HTML, CSS, JavaScript).
  2. Offers a small "API" the website asks for data: GET /api/cars

Start it with:   python -m uvicorn server:app --reload
Then open:       http://127.0.0.1:8000
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles

from cars import CARS, BRANDS, FUEL_PRICE, is_vintage, resale_value
from specs import spec_rows
from slug import slugify
from photos import get_photo

WEB_DIR = Path(__file__).parent / "web"

app = FastAPI(title="Roarwell Motors")


def car_to_json(car):
    """One car in the shape the website wants."""
    return {
        "id": slugify(car["name"]),
        "name": car["name"],
        "brand": car["brand"],
        "type": car["type"],
        "price": car["price"],
        "seats": car["seats"],
        "fuel": car["fuel"],
        "mpg": car["mpg"],
        "resale_pct": car["resale_5yr_pct"],
        "resale_value": resale_value(car),
        "resale_source": car["resale_source"],
        "vintage": is_vintage(car),
        "year": car.get("year"),
        "specs": [{"label": label, "value": value} for label, value in spec_rows(car)],
    }


@app.get("/api/cars")
def api_cars():
    """Every car, plus the little bits of data the page needs to do its own maths."""
    return {
        "cars": [car_to_json(car) for car in CARS],
        "brands": BRANDS,
        "fuel_price": FUEL_PRICE,
    }


BY_ID = {slugify(car["name"]): car for car in CARS}


@app.get("/api/photo/{car_id}")
def api_photo(car_id: str):
    """The car's photo (downloaded once from Wikimedia Commons, then kept in photo_cache/)."""
    car = BY_ID.get(car_id)
    found = get_photo(car["name"]) if car else None
    if not found:
        raise HTTPException(status_code=404, detail="no photo")
    return FileResponse(found[0], media_type="image/jpeg",
                        headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/photo/{car_id}/credit")
def api_photo_credit(car_id: str):
    """Who took the photo and under which licence (shown on the website)."""
    car = BY_ID.get(car_id)
    found = get_photo(car["name"]) if car else None
    if not found:
        raise HTTPException(status_code=404, detail="no photo")
    return found[1]


# ---------- Alex ----------

QUICK_REPLIES = {
    "passengers": ["1", "2", "4", "5", "7"],
    "fuel": ["petrol", "diesel", "electric", "hybrid", "no preference"],
    "budget": ["$20,000", "$30,000", "$40,000", "$60,000", "$100,000"],
    "commute": ["10 miles", "20 miles", "40 miles", "60 miles"],
    "brand": BRANDS + ["no preference"],
    "era": ["modern", "classic", "either"],
}


class ChatIn(BaseModel):
    """What the website sends: the new message plus everything Alex needs to remember."""
    text: str = ""
    prefs: dict = {}
    last_question: str = ""
    choices: list = []
    pending_car: str = ""


def _load_alex():
    """Load Alex's brain on first use, so the website still works if the AI key is missing."""
    import graph as brain
    return brain


@app.get("/api/alex/start")
def alex_start():
    """Alex's opening line."""
    try:
        brain = _load_alex()
    except Exception as problem:
        return {"ok": False, "reply": "Alex is resting right now (the AI is not set up). "
                                      "You can still browse every car on the page!", "error": repr(problem)}
    return {"ok": True, "reply": brain.QUESTIONS["name"], "last_question": brain.QUESTIONS["name"],
            "quick_replies": [], "prefs": {}}


@app.post("/api/chat")
def api_chat(body: ChatIn):
    try:
        brain = _load_alex()
        result = brain.graph.invoke({
            "user_text": body.text, "last_question": body.last_question, "prefs": body.prefs,
            "reply": "", "matches": [], "choices": body.choices, "pending_car": body.pending_car,
        })
    except Exception as problem:
        return {"ok": False, "reply": "Sorry, I had trouble reaching the AI. On a free plan this can be "
                                      "a rate limit, so please try again in a minute.", "error": repr(problem)}
    prefs = result["prefs"]
    pending = result.get("pending_car", "")
    choices = result.get("choices", [])
    if pending:
        quick = ["I'm choosing this car", "I'm still looking at other models"]
    elif choices:
        quick = list(choices)
    else:
        quick = QUICK_REPLIES.get(brain.missing_field(prefs), [])
    return {
        "ok": True,
        "reply": result["reply"],
        "cars": [{"id": slugify(c["name"]), "name": c["name"], "group": c.get("group", ""),
                  "price": c["price"], "resale_value": c["resale_value"], "resale_pct": c["resale_5yr_pct"],
                  "fuel_cost": c["fuel_cost"]} for c in result["matches"]],
        "specs": [{"label": l, "value": v} for l, v in result.get("specs", [])],
        "tagline": brain.TAGLINE,
        "quick_replies": quick,
        "prefs": prefs, "last_question": result["last_question"],
        "choices": choices, "pending_car": pending,
    }


# This must come LAST: it serves web/index.html at "/" and the other files beside it.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
