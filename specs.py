# specs.py - the spec sheet details for each car in cars.py.
#
# IMPORTANT: these are TYPICAL base-trim figures, rounded, from general knowledge.
# They are NOT looked up car by car, and real cars vary by model year and trim.
# Treat them as sample data for learning, and check a dealer's sheet before buying.

SPECS = {
    # ---- Toyota ----
    "Toyota Corolla":         {"engine": "2.0L 4-cylinder petrol",               "power": "~169 hp", "transmission": "CVT automatic",       "drivetrain": "Front-wheel drive"},
    "Toyota Camry":           {"engine": "2.5L 4-cylinder hybrid",               "power": "~225 hp", "transmission": "eCVT automatic",      "drivetrain": "Front-wheel drive (AWD available)"},
    "Toyota Prius":           {"engine": "2.0L 4-cylinder hybrid",               "power": "~196 hp", "transmission": "eCVT automatic",      "drivetrain": "Front-wheel drive (AWD available)"},
    "Toyota RAV4 Hybrid":     {"engine": "2.5L 4-cylinder hybrid",               "power": "~219 hp", "transmission": "eCVT automatic",      "drivetrain": "All-wheel drive"},
    "Toyota Grand Highlander":{"engine": "2.4L turbocharged 4-cylinder petrol",  "power": "~265 hp", "transmission": "8-speed automatic",   "drivetrain": "Front-wheel drive (AWD available)"},
    "Toyota Sienna":          {"engine": "2.5L 4-cylinder hybrid",               "power": "~245 hp", "transmission": "eCVT automatic",      "drivetrain": "Front-wheel drive (AWD available)"},
    "Toyota Tacoma":          {"engine": "2.4L turbocharged 4-cylinder petrol",  "power": "~228 hp", "transmission": "8-speed automatic",   "drivetrain": "Rear-wheel drive (4x4 available)"},

    # ---- Honda ----
    "Honda Civic":            {"engine": "2.0L 4-cylinder petrol",               "power": "~158 hp", "transmission": "CVT automatic",       "drivetrain": "Front-wheel drive"},
    "Honda HR-V":             {"engine": "2.0L 4-cylinder petrol",               "power": "~158 hp", "transmission": "CVT automatic",       "drivetrain": "Front-wheel drive (AWD available)"},
    "Honda CR-V":             {"engine": "1.5L turbocharged 4-cylinder petrol",  "power": "~190 hp", "transmission": "CVT automatic",       "drivetrain": "Front-wheel drive (AWD available)"},
    "Honda CR-V Hybrid":      {"engine": "2.0L 4-cylinder hybrid",               "power": "~204 hp", "transmission": "eCVT automatic",      "drivetrain": "Front-wheel drive (AWD available)"},
    "Honda Odyssey":          {"engine": "3.5L V6 petrol",                       "power": "~280 hp", "transmission": "10-speed automatic",  "drivetrain": "Front-wheel drive"},

    # ---- Hyundai ----
    "Hyundai Elantra":        {"engine": "2.0L 4-cylinder petrol",               "power": "~147 hp", "transmission": "CVT automatic",       "drivetrain": "Front-wheel drive"},
    "Hyundai Elantra Hybrid": {"engine": "1.6L 4-cylinder hybrid",               "power": "~139 hp", "transmission": "6-speed dual-clutch automatic", "drivetrain": "Front-wheel drive"},
    "Hyundai Tucson Hybrid":  {"engine": "1.6L turbocharged 4-cylinder hybrid",  "power": "~226 hp", "transmission": "6-speed automatic",   "drivetrain": "Front- or all-wheel drive"},
    "Hyundai Palisade":       {"engine": "3.8L V6 petrol",                       "power": "~291 hp", "transmission": "8-speed automatic",   "drivetrain": "Front-wheel drive (AWD available)"},
    "Hyundai Ioniq 5":        {"engine": "Electric motor(s)",                    "power": "~225-320 hp", "transmission": "Single-speed automatic", "drivetrain": "Rear- or all-wheel drive", "range": "~260-320 miles per charge"},

    # ---- Kia ----
    "Kia Sportage Hybrid":    {"engine": "1.6L turbocharged 4-cylinder hybrid",  "power": "~227 hp", "transmission": "6-speed automatic",   "drivetrain": "Front-wheel drive (AWD available)"},
    "Kia Telluride":          {"engine": "3.8L V6 petrol",                       "power": "~291 hp", "transmission": "8-speed automatic",   "drivetrain": "Front-wheel drive (AWD available)"},
    "Kia Carnival":           {"engine": "3.5L V6 petrol",                       "power": "~290 hp", "transmission": "8-speed automatic",   "drivetrain": "Front-wheel drive"},

    # ---- Ford ----
    "Ford Maverick Hybrid":   {"engine": "2.5L 4-cylinder hybrid",               "power": "~191 hp", "transmission": "eCVT automatic",      "drivetrain": "Front-wheel drive"},
    "Ford Escape Hybrid":     {"engine": "2.5L 4-cylinder hybrid",               "power": "~200 hp", "transmission": "eCVT automatic",      "drivetrain": "Front-wheel drive (AWD available)"},
    "Ford F-150":             {"engine": "2.7L twin-turbo V6 petrol",            "power": "~325 hp", "transmission": "10-speed automatic",  "drivetrain": "Rear-wheel drive (4x4 available)"},
    "Ford Mustang Mach-E":    {"engine": "Electric motor(s)",                    "power": "~266-480 hp", "transmission": "Single-speed automatic", "drivetrain": "Rear- or all-wheel drive", "range": "~250-320 miles per charge"},

    # ---- Tesla ----
    "Tesla Model 3":          {"engine": "Electric motor(s)",                    "power": "~280-500 hp", "transmission": "Single-speed automatic", "drivetrain": "Rear- or all-wheel drive", "range": "~270-360 miles per charge"},
    "Tesla Model Y":          {"engine": "Electric motor(s)",                    "power": "~295-500 hp", "transmission": "Single-speed automatic", "drivetrain": "Rear- or all-wheel drive", "range": "~310-330 miles per charge"},

    # ---- Mazda ----
    "Mazda3 Hatchback":       {"engine": "2.5L 4-cylinder petrol",               "power": "~191 hp", "transmission": "6-speed automatic",   "drivetrain": "Front-wheel drive (AWD available)"},
    "Mazda CX-5":             {"engine": "2.5L 4-cylinder petrol",               "power": "~187 hp", "transmission": "6-speed automatic",   "drivetrain": "All-wheel drive"},

    # ---- More variety ----
    "Subaru Outback": {"engine": "2.5L flat-4 petrol", "power": "~182 hp", "transmission": "CVT automatic", "drivetrain": "All-wheel drive (standard)"},
    "Subaru Crosstrek": {"engine": "2.0L flat-4 petrol", "power": "~152 hp", "transmission": "CVT automatic", "drivetrain": "All-wheel drive (standard)"},
    "Chevrolet Equinox": {"engine": "1.5L turbocharged 4-cylinder petrol", "power": "~175 hp", "transmission": "6-speed automatic", "drivetrain": "Front-wheel drive (AWD available)"},
    "Chevrolet Silverado 1500": {"engine": "2.7L turbocharged 4-cylinder petrol", "power": "~310 hp", "transmission": "8-speed automatic", "drivetrain": "Rear-wheel drive (4x4 available)"},
    "Ram 1500": {"engine": "3.0L turbocharged inline-6 petrol", "power": "~420 hp", "transmission": "8-speed automatic", "drivetrain": "Rear-wheel drive (4x4 available)"},
    "Jeep Wrangler": {"engine": "2.0L turbocharged 4-cylinder petrol", "power": "~270 hp", "transmission": "8-speed automatic", "drivetrain": "4x4 (standard)"},
    "Nissan Rogue": {"engine": "1.5L turbocharged 3-cylinder petrol", "power": "~201 hp", "transmission": "CVT automatic", "drivetrain": "Front-wheel drive (AWD available)"},
    "Volkswagen Jetta": {"engine": "1.5L turbocharged 4-cylinder petrol", "power": "~158 hp", "transmission": "8-speed automatic", "drivetrain": "Front-wheel drive"},
    "BMW 3 Series": {"engine": "2.0L turbocharged 4-cylinder petrol", "power": "~255 hp", "transmission": "8-speed automatic", "drivetrain": "Rear-wheel drive (AWD available)"},
    "Lexus RX Hybrid": {"engine": "2.5L 4-cylinder hybrid", "power": "~246 hp", "transmission": "eCVT automatic", "drivetrain": "All-wheel drive"},
    "Kia EV6": {"engine": "Electric motor(s)", "power": "~225-320 hp", "transmission": "Single-speed automatic", "drivetrain": "Rear-wheel drive (AWD available)", "range": "~250-310 miles depending on version"},

    # ---- Vintage cars (engines varied a lot by order options) ----
    "1969 Ford Mustang Mach 1": {"engine": "351 cu in (5.8L) V8 petrol (428 cu in V8 optional)", "power": "~290 hp (351 V8); 335-360 hp with the 428 V8", "transmission": "3-speed automatic or 4-speed manual", "drivetrain": "Rear-wheel drive"},
    "1965 Ford Mustang":        {"engine": "289 cu in (4.7L) V8 petrol (six-cylinder also offered)", "power": "~200-271 hp (289 V8)", "transmission": "3-speed or 4-speed manual, or 3-speed automatic", "drivetrain": "Rear-wheel drive"},
    "1969 Chevrolet Camaro":    {"engine": "350 cu in (5.7L) V8 petrol (327 V8 and six-cylinder also offered)", "power": "~255-300 hp (350 V8)", "transmission": "3-speed or 4-speed manual, or automatic", "drivetrain": "Rear-wheel drive"},
    "1967 Chevrolet Corvette Stingray": {"engine": "327 cu in (5.4L) V8 petrol (427 V8 also offered)", "power": "~300-435 hp (varied by engine)", "transmission": "4-speed manual (automatic also offered)", "drivetrain": "Rear-wheel drive"},
    "1970 Dodge Challenger R/T": {"engine": "383 cu in (6.3L) V8 petrol (440 and 426 V8 also offered)", "power": "~335-425 hp (varied by engine)", "transmission": "3-speed automatic or 4-speed manual", "drivetrain": "Rear-wheel drive"},
    "1957 Chevrolet Bel Air": {"engine": "283 cu in (4.6L) V8 petrol (six-cylinder also offered)", "power": "~185-283 hp (varied by engine)", "transmission": "3-speed manual or 2-speed automatic", "drivetrain": "Rear-wheel drive"},
}


def spec_rows(car):
    """The spec sheet for one car as (label, value) rows, ready to show as a table."""
    spec = SPECS[car["name"]]
    electric = car["fuel"] == "electric"
    vintage = car.get("vintage", False)

    rows = [
        ("Model", car["name"]),
        ("Model year", str(car["year"]) if vintage else "Current generation"),
        ("Body type", car["type"].title()),
        ("Fuel type", car["fuel"].title()),
        ("Engine", spec["engine"]),
        ("Power", spec["power"]),
        ("Transmission", spec["transmission"]),
        ("Drivetrain", spec["drivetrain"]),
        ("Seats", str(car["seats"])),
        ("Fuel economy", f"~{car['mpg']} {'MPGe' if electric else 'MPG'} (combined)"),
    ]
    if electric:
        rows.append(("Range", spec["range"]))
    rows.append(("Price (sample)", f"${car['price']:,}"))
    return rows
