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

from cars import CARS, BRANDS, FUEL_PRICE, is_vintage, resale_value, slugify
from specs import spec_rows
from photos import get_photo
import agent

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


# ---------- Alex (the AI agent) ----------

class ChatIn(BaseModel):
    """What the website sends: the new message, the recent chat, and what Alex has learned."""
    text: str = ""
    history: list = []
    memory: dict = {}


_llm = None


def explain_problem(problem):
    """Turn a scary error into a sentence a human can act on."""
    text = repr(problem)
    low = text.lower()
    if "groq_api_key" in low:
        return "Alex needs his AI key. Open the .env file next to server.py and add a line: GROQ_API_KEY=your_key_here, then restart the server."
    if "modulenotfounderror" in low or "no module named" in low:
        return "A Python library is missing. Run: .venv/bin/python -m pip install langchain-groq python-dotenv"
    if "429" in low or "rate" in low and "limit" in low:
        return "The free AI plan is busy (rate limit). Wait a minute and try again."
    if "401" in low or "invalid api key" in low or "authentication" in low:
        return "The AI key was rejected. Check that GROQ_API_KEY in .env is correct (no quotes or spaces)."
    if "404" in low or "model" in low and "not" in low and "found" in low:
        return "The AI model name was not found. Run list_models.py to see which models your key can use."
    if "connect" in low or "timeout" in low or "network" in low:
        return "I could not reach the AI service. Check your internet connection."
    return "Something went wrong talking to the AI."


@app.get("/api/alex/start")
def alex_start():
    """Alex's opening line, plus a quick health check so problems show up straight away."""
    out = {"reply": agent.GREETING, "chips": agent.GREETING_CHIPS, "ok": True}
    try:
        global _llm
        _llm = _llm or agent.get_llm()
    except Exception as problem:
        out.update(ok=False, problem=explain_problem(problem), detail=repr(problem))
    return out


@app.post("/api/agent")
def api_agent(body: ChatIn):
    global _llm
    try:
        _llm = _llm or agent.get_llm()
        result = agent.run_agent(_llm, body.text, body.history, body.memory)
    except Exception as problem:
        return {"ok": False, "reply": "Sorry, I hit a problem and couldn't answer that.",
                "problem": explain_problem(problem), "detail": repr(problem)[:400]}
    return {"ok": True, **result}


@app.middleware("http")
async def no_stale_files(request, call_next):
    """Make the browser re-check the website files each time, so an updated app.js or alex.js is never replaced by an old cached copy."""
    response = await call_next(request)
    if not request.url.path.startswith("/api") and "cache-control" not in response.headers:
        response.headers["Cache-Control"] = "no-cache"
    return response


# This must come LAST: it serves web/index.html at "/" and the other files beside it.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
