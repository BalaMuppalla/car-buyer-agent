"""traits.py - "what can I use this car for?" facts, worked out from our own data.

Alex uses this to answer questions like "can I tow a boat with it?" or "is it good for camping?"
without making things up. Everything here is APPROXIMATE and rounded: it is meant to give a sensible
first answer, and Alex tells people to check the maker's guide for the exact trim they want.
"""
from specs import SPECS

# Rough towing ability by body type (typical, depends a lot on engine and trim).
TOWING_BY_TYPE = {
    "sedan": "not meant for towing (under about 1,500 lb, if at all)",
    "hatchback": "not meant for towing (under about 1,500 lb, if at all)",
    "coupe": "not meant for towing",
    "suv": "light to medium (roughly 1,500-3,500 lb, depending on trim)",
    "minivan": "medium (roughly 3,500 lb)",
    "truck": "heavy (roughly 3,500 to 10,000+ lb, depending on trim)",
}
TOWING_OVERRIDES = {
    "Ford Maverick Hybrid": "light to medium (roughly 2,000-4,000 lb depending on setup)",
    "Ford F-150": "heavy (up to roughly 13,000 lb on the right setup)",
    "Chevrolet Silverado 1500": "heavy (up to roughly 13,000 lb on the right setup)",
    "Ram 1500": "heavy (up to roughly 11,000-12,000 lb on the right setup)",
    "Toyota Tacoma": "medium to heavy (up to roughly 6,000 lb)",
    "Jeep Wrangler": "medium (roughly 3,500 lb)",
    "Hyundai Palisade": "medium (roughly 5,000 lb)",
    "Kia Telluride": "medium (roughly 5,000 lb)",
    "Toyota Grand Highlander": "medium (roughly 5,000 lb on some trims)",
    "Honda HR-V": "very light (about 1,000 lb)",
    "Toyota RAV4 Hybrid": "light (about 1,750 lb)",
    "Honda CR-V": "light (about 1,500 lb)",
    "Honda CR-V Hybrid": "light (about 1,000 lb)",
}

CARGO_BY_TYPE = {
    "sedan": "trunk only: fine for luggage and groceries, not for bulky items",
    "hatchback": "hatchback with folding seats: fits bulky items better than a sedan",
    "coupe": "limited space",
    "suv": "roomy, and it grows a lot with the rear seats folded",
    "minivan": "the most interior room of any type, with sliding doors that are easy in tight parking spots",
    "truck": "an open bed for dirty, tall or heavy loads (weather and security are the trade-offs)",
}


def drivetrain(car):
    return SPECS[car["name"]]["drivetrain"]


def awd_note(car):
    d = drivetrain(car).lower()
    if "standard" in d or d in ("all-wheel drive", "4x4"):
        return "All-wheel or four-wheel drive comes standard, so it copes well with snow, mud and gravel roads."
    if "awd" in d or "4x4" in d or "all-wheel" in d:
        return "All-wheel or four-wheel drive is available as an option, which helps in snow and on rough roads."
    if car.get("vintage"):
        return "Rear-wheel drive and old tyre technology: not a good choice for snow or rough roads."
    return "Two-wheel drive only, fine for paved roads but weaker in deep snow or mud."


def profile(car):
    """A dictionary of plain-language facts about what the car is good (and not so good) for."""
    t = car["type"]
    vintage = car.get("vintage", False)
    notes = []
    if vintage:
        towing = "not recommended: an old car not built for towing"
        cargo = "limited, and old cars have few safety features and no modern conveniences"
        notes.append("A collector car: best for weekend drives, shows and fun, not for daily errands or long trips.")
    else:
        towing = TOWING_OVERRIDES.get(car["name"], TOWING_BY_TYPE[t])
        cargo = CARGO_BY_TYPE[t]
        if car["fuel"] == "electric":
            towing = "light (EVs lose driving range quickly when towing). " + towing
    seats = car["seats"]
    mpg = car["mpg"]
    return {
        "towing": towing,
        "cargo": cargo,
        "bad_weather_and_rough_roads": awd_note(car),
        "family": (f"Seats {seats}." + (" Sliding doors make loading kids and car seats easy." if t == "minivan" else "")),
        "commuting": ("Very cheap to run for daily driving." if mpg >= 45 and not vintage else
                      "Reasonable running costs." if mpg >= 28 else "Thirsty: expect higher fuel costs for daily driving."),
        "ride_sharing_or_delivery_work": ("A good fit: efficient and comfortable." if car["fuel"] in ("hybrid", "electric") and not vintage
                                          else "Possible, but fuel costs will be higher than a hybrid or EV."),
        "camping_and_road_trips": (
            "Great for camping: space, rough-road ability and room for gear." if t in ("suv", "truck", "minivan") and "standard" in drivetrain(car).lower() or t == "minivan"
            else "Fine for road trips and light camping." if t in ("suv", "truck") else "Fine for road trips, but little room for camping gear."),
        "notes": notes,
    }
