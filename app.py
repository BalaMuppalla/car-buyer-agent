"""app.py - the terminal chat. It only talks to the user; all thinking is in graph.py."""
from cars import is_vintage
from graph import graph, QUESTIONS, TAGLINE


def show_cars(matches, commute):
    """Print the recommended cars as clean lines (the browser UI shows cards instead)."""
    titles = {"chosen": "The car you asked about:", "brand": "Your favorite brand:", "top": "Our top picks for you:",
              "other": "Other options in your price range:"}
    for group in ("chosen", "brand", "top", "other"):
        group_cars = [m for m in matches if m["group"] == group]
        if not group_cars:
            continue
        print(titles[group])
        for m in group_cars:
            tag = " (classic)" if is_vintage(m) else ""
            estimate = " (estimate)" if m["resale_source"] == "estimate" else ""
            print(f"  - {m['name']}{tag} | ${m['price']:,} | {m['seats']} seats | {m['fuel']}")
            print(f"      Worth after 5 years: about ${m['resale_value']:,} "
                  f"(keeps {m['resale_5yr_pct']}% of its price){estimate}")
            print(f"      Yearly fuel cost: about ${m['fuel_cost']:,} "
                  f"(for your {commute} miles a day)")
        print()


def show_specs(rows):
    """Print the spec sheet as an aligned table."""
    width = max(len(label) for label, _ in rows)
    print("  " + "-" * (width + 40))
    for label, value in rows:
        print(f"  {label:<{width}} | {value}")
    print("  " + "-" * (width + 40))
    print(f"\n  {TAGLINE}\n")


prefs = {}
last_question = QUESTIONS["name"]
choices = []
pending_car = ""

print(f"\nAlex: {last_question}")
print("(type 'quit' to exit)\n")

while True:
    user_text = input("You: ")
    if user_text.strip().lower() in ("quit", "exit"):
        break

    result = graph.invoke({
        "user_text": user_text,
        "last_question": last_question,
        "prefs": prefs,
        "reply": "",
        "matches": [],
        "choices": choices,
        "pending_car": pending_car,
    })

    prefs = result["prefs"]
    last_question = result["last_question"]
    choices = result.get("choices", [])
    pending_car = result.get("pending_car", "")
    print(f"\nAlex: {result['reply']}\n")
    show_cars(result["matches"], prefs.get("commute"))
    if result.get("specs"):
        show_specs(result["specs"])
    if result["matches"] and not pending_car:
        print("Tip: type a car's name for details (short names work, like 'camry' or "
              "'toyota hybrid'), or change an answer (like 'budget 60000').\n")