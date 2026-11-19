# cars.py - our "car lot": the facts Alex is allowed to recommend from.
#
# IMPORTANT: this is SAMPLE data for learning.
# - price: rounded, approximate starting prices in US dollars (not live prices)
# - mpg: approximate combined fuel economy (electric cars use MPGe)
# - resale_5yr_pct: % of the original price a car keeps after 5 years, on the
#   "% of sticker price" scale (industry average is about 45%).
#   resale_source = "published" means the figure came from a published 2026
#   resale ranking; "estimate" means it is my rough estimate, not a real figure.

MODERN_CARS = [
    # ---- Toyota ----
    {"name": "Toyota Corolla",        "brand": "Toyota", "type": "sedan",     "price": 23000, "seats": 5, "fuel": "petrol",   "mpg": 35,  "resale_5yr_pct": 50, "resale_source": "estimate"},
    {"name": "Toyota Camry",          "brand": "Toyota", "type": "sedan",     "price": 29000, "seats": 5, "fuel": "hybrid",   "mpg": 52,  "resale_5yr_pct": 52, "resale_source": "published"},
    {"name": "Toyota Prius",          "brand": "Toyota", "type": "hatchback", "price": 29000, "seats": 5, "fuel": "hybrid",   "mpg": 57,  "resale_5yr_pct": 53, "resale_source": "published"},
    {"name": "Toyota RAV4 Hybrid",    "brand": "Toyota", "type": "suv",       "price": 33000, "seats": 5, "fuel": "hybrid",   "mpg": 40,  "resale_5yr_pct": 54, "resale_source": "estimate"},
    {"name": "Toyota Grand Highlander","brand": "Toyota", "type": "suv",      "price": 46000, "seats": 7, "fuel": "petrol",   "mpg": 24,  "resale_5yr_pct": 51, "resale_source": "published"},
    {"name": "Toyota Sienna",         "brand": "Toyota", "type": "minivan",   "price": 40000, "seats": 7, "fuel": "hybrid",   "mpg": 36,  "resale_5yr_pct": 54, "resale_source": "published"},
    {"name": "Toyota Tacoma",         "brand": "Toyota", "type": "truck",     "price": 34000, "seats": 5, "fuel": "petrol",   "mpg": 22,  "resale_5yr_pct": 63, "resale_source": "published"},

    # ---- Honda ----
    {"name": "Honda Civic",           "brand": "Honda",  "type": "sedan",     "price": 25000, "seats": 5, "fuel": "petrol",   "mpg": 36,  "resale_5yr_pct": 52, "resale_source": "published"},
    {"name": "Honda HR-V",            "brand": "Honda",  "type": "suv",       "price": 26000, "seats": 5, "fuel": "petrol",   "mpg": 28,  "resale_5yr_pct": 50, "resale_source": "published"},
    {"name": "Honda CR-V",            "brand": "Honda",  "type": "suv",       "price": 32000, "seats": 5, "fuel": "petrol",   "mpg": 30,  "resale_5yr_pct": 53, "resale_source": "published"},
    {"name": "Honda CR-V Hybrid",     "brand": "Honda",  "type": "suv",       "price": 35000, "seats": 5, "fuel": "hybrid",   "mpg": 37,  "resale_5yr_pct": 53, "resale_source": "estimate"},
    {"name": "Honda Odyssey",         "brand": "Honda",  "type": "minivan",   "price": 42000, "seats": 8, "fuel": "petrol",   "mpg": 22,  "resale_5yr_pct": 45, "resale_source": "estimate"},

    # ---- Hyundai ----
    {"name": "Hyundai Elantra",       "brand": "Hyundai","type": "sedan",     "price": 22000, "seats": 5, "fuel": "petrol",   "mpg": 36,  "resale_5yr_pct": 42, "resale_source": "estimate"},
    {"name": "Hyundai Elantra Hybrid","brand": "Hyundai","type": "sedan",     "price": 26000, "seats": 5, "fuel": "hybrid",   "mpg": 54,  "resale_5yr_pct": 42, "resale_source": "estimate"},
    {"name": "Hyundai Tucson Hybrid", "brand": "Hyundai","type": "suv",       "price": 34000, "seats": 5, "fuel": "hybrid",   "mpg": 38,  "resale_5yr_pct": 44, "resale_source": "estimate"},
    {"name": "Hyundai Palisade",      "brand": "Hyundai","type": "suv",       "price": 40000, "seats": 8, "fuel": "petrol",   "mpg": 22,  "resale_5yr_pct": 44, "resale_source": "estimate"},
    {"name": "Hyundai Ioniq 5",       "brand": "Hyundai","type": "suv",       "price": 42000, "seats": 5, "fuel": "electric", "mpg": 114, "resale_5yr_pct": 35, "resale_source": "estimate"},

    # ---- Kia ----
    {"name": "Kia Sportage Hybrid",   "brand": "Kia",    "type": "suv",       "price": 33000, "seats": 5, "fuel": "hybrid",   "mpg": 43,  "resale_5yr_pct": 43, "resale_source": "estimate"},
    {"name": "Kia Telluride",         "brand": "Kia",    "type": "suv",       "price": 38000, "seats": 7, "fuel": "petrol",   "mpg": 23,  "resale_5yr_pct": 45, "resale_source": "estimate"},
    {"name": "Kia Carnival",          "brand": "Kia",    "type": "minivan",   "price": 36000, "seats": 8, "fuel": "petrol",   "mpg": 22,  "resale_5yr_pct": 42, "resale_source": "estimate"},

    # ---- Ford ----
    {"name": "Ford Maverick Hybrid",  "brand": "Ford",   "type": "truck",     "price": 28000, "seats": 5, "fuel": "hybrid",   "mpg": 42,  "resale_5yr_pct": 54, "resale_source": "published"},
    {"name": "Ford Escape Hybrid",    "brand": "Ford",   "type": "suv",       "price": 33000, "seats": 5, "fuel": "hybrid",   "mpg": 40,  "resale_5yr_pct": 42, "resale_source": "estimate"},
    {"name": "Ford F-150",            "brand": "Ford",   "type": "truck",     "price": 40000, "seats": 5, "fuel": "petrol",   "mpg": 20,  "resale_5yr_pct": 48, "resale_source": "estimate"},
    {"name": "Ford Mustang Mach-E",   "brand": "Ford",   "type": "suv",       "price": 40000, "seats": 5, "fuel": "electric", "mpg": 100, "resale_5yr_pct": 32, "resale_source": "estimate"},

    # ---- Tesla ----
    {"name": "Tesla Model 3",         "brand": "Tesla",  "type": "sedan",     "price": 40000, "seats": 5, "fuel": "electric", "mpg": 130, "resale_5yr_pct": 35, "resale_source": "published"},
    {"name": "Tesla Model Y",         "brand": "Tesla",  "type": "suv",       "price": 45000, "seats": 5, "fuel": "electric", "mpg": 123, "resale_5yr_pct": 34, "resale_source": "estimate"},

    # ---- Mazda ----
    {"name": "Mazda3 Hatchback",      "brand": "Mazda",  "type": "hatchback", "price": 25000, "seats": 5, "fuel": "petrol",   "mpg": 31,  "resale_5yr_pct": 45, "resale_source": "estimate"},
    {"name": "Mazda CX-5",            "brand": "Mazda",  "type": "suv",       "price": 31000, "seats": 5, "fuel": "petrol",   "mpg": 28,  "resale_5yr_pct": 46, "resale_source": "estimate"},

    # ---- More variety (added later; same rounded sample numbers) ----
    {"name": "Subaru Outback", "brand": "Subaru", "type": "suv", "price": 30000, "seats": 5, "fuel": "petrol", "mpg": 29, "resale_5yr_pct": 50, "resale_source": "estimate"},
    {"name": "Subaru Crosstrek", "brand": "Subaru", "type": "suv", "price": 27000, "seats": 5, "fuel": "petrol", "mpg": 29, "resale_5yr_pct": 52, "resale_source": "estimate"},
    {"name": "Chevrolet Equinox", "brand": "Chevrolet", "type": "suv", "price": 30000, "seats": 5, "fuel": "petrol", "mpg": 30, "resale_5yr_pct": 44, "resale_source": "estimate"},
    {"name": "Chevrolet Silverado 1500", "brand": "Chevrolet", "type": "truck", "price": 38000, "seats": 5, "fuel": "petrol", "mpg": 20, "resale_5yr_pct": 52, "resale_source": "estimate"},
    {"name": "Ram 1500", "brand": "Ram", "type": "truck", "price": 40000, "seats": 5, "fuel": "petrol", "mpg": 21, "resale_5yr_pct": 48, "resale_source": "estimate"},
    {"name": "Jeep Wrangler", "brand": "Jeep", "type": "suv", "price": 35000, "seats": 5, "fuel": "petrol", "mpg": 20, "resale_5yr_pct": 60, "resale_source": "estimate"},
    {"name": "Nissan Rogue", "brand": "Nissan", "type": "suv", "price": 29000, "seats": 5, "fuel": "petrol", "mpg": 30, "resale_5yr_pct": 42, "resale_source": "estimate"},
    {"name": "Volkswagen Jetta", "brand": "Volkswagen", "type": "sedan", "price": 22000, "seats": 5, "fuel": "petrol", "mpg": 33, "resale_5yr_pct": 43, "resale_source": "estimate"},
    {"name": "BMW 3 Series", "brand": "BMW", "type": "sedan", "price": 46000, "seats": 5, "fuel": "petrol", "mpg": 30, "resale_5yr_pct": 40, "resale_source": "estimate"},
    {"name": "Lexus RX Hybrid", "brand": "Lexus", "type": "suv", "price": 55000, "seats": 5, "fuel": "hybrid", "mpg": 36, "resale_5yr_pct": 55, "resale_source": "estimate"},
    {"name": "Kia EV6", "brand": "Kia", "type": "suv", "price": 43000, "seats": 5, "fuel": "electric", "mpg": 117, "resale_5yr_pct": 40, "resale_source": "estimate"},
]

# ---- Vintage (classic) cars ----
# Classics work differently from new cars: they don't reliably lose value.
# Their prices move with the collector market and can go up OR down, so
# resale_5yr_pct = 100 here just means "expected to roughly hold its value".
# Prices are typical "good condition" sample prices; real sales vary a lot
# (published sales of the 1969 Mach 1 range from about $35,000 to $133,000).
# mpg values are rough estimates for these old V8 engines.
VINTAGE_CARS = [
    {"name": "1969 Ford Mustang Mach 1",  "brand": "Ford",      "type": "coupe", "price": 75000, "seats": 4, "fuel": "petrol", "mpg": 14, "resale_5yr_pct": 100, "resale_source": "estimate", "year": 1969, "vintage": True},
    {"name": "1965 Ford Mustang",         "brand": "Ford",      "type": "coupe", "price": 35000, "seats": 4, "fuel": "petrol", "mpg": 17, "resale_5yr_pct": 100, "resale_source": "estimate", "year": 1965, "vintage": True},
    {"name": "1969 Chevrolet Camaro",     "brand": "Chevrolet", "type": "coupe", "price": 45000, "seats": 4, "fuel": "petrol", "mpg": 14, "resale_5yr_pct": 100, "resale_source": "estimate", "year": 1969, "vintage": True},
    {"name": "1967 Chevrolet Corvette Stingray", "brand": "Chevrolet", "type": "coupe", "price": 85000, "seats": 2, "fuel": "petrol", "mpg": 15, "resale_5yr_pct": 100, "resale_source": "estimate", "year": 1967, "vintage": True},
    {"name": "1970 Dodge Challenger R/T", "brand": "Dodge", "type": "coupe", "price": 90000, "seats": 4, "fuel": "petrol", "mpg": 14, "resale_5yr_pct": 100, "resale_source": "estimate", "year": 1970, "vintage": True},
    {"name": "1957 Chevrolet Bel Air", "brand": "Chevrolet", "type": "sedan", "price": 70000, "seats": 6, "fuel": "petrol", "mpg": 15, "resale_5yr_pct": 100, "resale_source": "estimate", "year": 1957, "vintage": True},
]

# Everything together. Brand-first works the same for vintage and modern cars.
CARS = MODERN_CARS + VINTAGE_CARS

BRANDS = sorted({car["brand"] for car in CARS})


# ---- Helper functions: small calculations on one car ----

# Rough fuel/energy cost per gallon (or gallon-equivalent for electric), in dollars.
# Electric: about 33.7 kWh = 1 "gallon equivalent", at roughly $0.17 per kWh.
FUEL_PRICE = {"petrol": 3.50, "hybrid": 3.50, "diesel": 4.00, "electric": 5.70}


def is_vintage(car):
    """True for classic cars. Modern cars don't have the 'vintage' key."""
    return car.get("vintage", False)


def resale_value(car):
    """Estimated dollar value of the car after 5 years."""
    return round(car["price"] * car["resale_5yr_pct"] / 100)


def yearly_fuel_cost(car, miles_per_day):
    """Estimated fuel/charging cost per year for a daily commute."""
    gallons_per_year = miles_per_day * 365 / car["mpg"]
    return round(gallons_per_year * FUEL_PRICE[car["fuel"]])


def slugify(name):
    """'Honda CR-V Hybrid' -> 'honda-cr-v-hybrid': a safe id for the website."""
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
