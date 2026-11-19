"""ui.py - the FACE of Alex: a chat page in the browser.

It only shows things and collects clicks. All the thinking happens in graph.py.
Run it with:  streamlit run ui.py
"""
import streamlit as st

from cars import BRANDS, is_vintage
from graph import graph, missing_field, QUESTIONS, TAGLINE

st.set_page_config(page_title="Alex - Car Buyer Agent", page_icon="🚗")

# Buttons shown under the chat for each question (so the user can tap instead of type).
QUICK_REPLIES = {
    "passengers": ["1", "2", "4", "5", "7"],
    "fuel": ["petrol", "diesel", "electric", "hybrid", "no preference"],
    "budget": ["$20,000", "$30,000", "$40,000", "$60,000", "$100,000"],
    "commute": ["10 miles", "20 miles", "40 miles", "60 miles"],
    "brand": BRANDS + ["no preference"],
    "era": ["modern", "classic", "either"],
}

GROUP_TITLES = {
    "chosen": "The car you asked about",
    "brand": "Your favorite brand",
    "top": "Our top picks for you",
    "other": "Other options in your price range",
}


# ---------- Session state: the app's memory ----------
# Streamlit re-runs this whole file on every click, so anything we want to
# remember (the chat, what Alex has learned) must live in st.session_state.

def reset():
    st.session_state.messages = [
        {"role": "assistant", "content": QUESTIONS["name"], "cars": []}
    ]
    st.session_state.prefs = {}
    st.session_state.last_question = QUESTIONS["name"]
    st.session_state.choices = []
    st.session_state.pending_car = ""
    st.session_state.pop("pending", None)
    st.session_state.pop("error", None)


if "messages" not in st.session_state:
    reset()


def queue_message(text):
    """Called when a quick-reply button is clicked: act as if the user typed it."""
    st.session_state.pending = text


# ---------- Handle new input (typed or clicked) ----------

user_text = st.chat_input("Type your answer here...")
if "pending" in st.session_state:
    user_text = st.session_state.pop("pending")

if user_text:
    st.session_state.pop("error", None)
    st.session_state.messages.append({"role": "user", "content": user_text, "cars": []})
    try:
        with st.spinner("Alex is thinking..."):
            result = graph.invoke({
                "user_text": user_text,
                "last_question": st.session_state.last_question,
                "prefs": st.session_state.prefs,
                "reply": "",
                "matches": [],
                "choices": st.session_state.choices,
                "pending_car": st.session_state.pending_car,
            })
    except Exception as problem:
        # e.g. the free tier's rate limit. Don't crash the page: apologise and keep the chat.
        st.session_state.error = repr(problem)
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Sorry, I had trouble reaching the AI. If you're on a free plan "
                       "this can be a rate limit, so please try again in a minute.",
            "cars": [],
        })
    else:
        st.session_state.prefs = result["prefs"]
        st.session_state.last_question = result["last_question"]
        st.session_state.choices = result.get("choices", [])
        st.session_state.pending_car = result.get("pending_car", "")
        st.session_state.messages.append(
            {"role": "assistant", "content": result["reply"], "cars": result["matches"],
             "specs": result.get("specs", [])}
        )


# ---------- Sidebar: what Alex has learned so far ----------

with st.sidebar:
    st.header("About you")
    p = st.session_state.prefs
    budget = f"${p['budget']:,}" if p.get("budget") else "—"
    commute = f"{p['commute']} miles/day" if p.get("commute") else "—"
    st.write(f"🙂 Name: {p.get('name') or '—'}")
    st.write(f"👥 Passengers: {p.get('passengers') or '—'}")
    st.write(f"⛽ Fuel: {p.get('fuel') or '—'}")
    st.write(f"💰 Budget: {budget}")
    st.write(f"🛣️ Commute: {commute}")
    st.write(f"🏷️ Brand: {p.get('brand') or '—'}")
    st.write(f"🕰️ Era: {p.get('era') or '—'}")
    st.button("🔄 Start over", on_click=reset)
    if "error" in st.session_state:
        with st.expander("Technical details"):
            st.code(st.session_state.error)


# ---------- Main area: the chat ----------

def show_car(car):
    """One car as a card."""
    commute = st.session_state.prefs.get("commute")
    with st.container(border=True):
        st.subheader(car["name"] + ("  🏁 Classic" if is_vintage(car) else ""))
        c1, c2, c3 = st.columns(3)
        c1.metric("Price", f"${car['price']:,}")
        c2.metric("Seats", car["seats"])
        c3.metric("Fuel type", car["fuel"].title())
        c4, c5 = st.columns(2)
        c4.metric("Worth after 5 years", f"${car['resale_value']:,}",
                  help="What you could expect to sell it for in 5 years.")
        c5.metric("Yearly fuel cost", f"${car['fuel_cost']:,}",
                  help=f"Estimated cost of fuel (or charging) for {commute} miles a day.")
        estimate = " (estimate)" if car["resale_source"] == "estimate" else ""
        st.caption(f"Keeps about {car['resale_5yr_pct']}% of its price after 5 years{estimate}. "
                   f"Fuel cost is for your {commute} miles a day.")
        if is_vintage(car):
            st.caption("Collector car: its value can go up or down.")


st.title("🚗 Alex, your car buyer agent")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        for group in ("chosen", "brand", "top", "other"):
            group_cars = [c for c in message["cars"] if c["group"] == group]
            if group_cars:
                st.markdown(f"**{GROUP_TITLES[group]}**")
                for car in group_cars:
                    show_car(car)
        if message.get("specs"):
            table = "| Spec | Details |\n|---|---|\n" + "\n".join(
                f"| **{label}** | {value} |" for label, value in message["specs"])
            st.markdown(table)
            st.success(TAGLINE)

if st.session_state.messages[-1]["cars"] and not st.session_state.pending_car:
    st.caption("Type a car's name for details (short names work, like 'camry' or 'toyota hybrid'), "
               "or change any answer (like 'budget 60000').")


# ---------- Quick-reply buttons ----------

if st.session_state.pending_car:
    # Alex asked "choosing this car, or still looking?": two buttons.
    left, right = st.columns(2)
    left.button("✅ I'm choosing this car", key="decide-yes",
                on_click=queue_message, args=("I'm choosing this car",))
    right.button("🔍 Still looking at other models", key="decide-no",
                 on_click=queue_message, args=("I'm still looking at other models",))
elif st.session_state.choices:
    # Alex asked "which one do you mean?": one button per car.
    names = st.session_state.choices
    for start in range(0, len(names), 3):
        row = names[start:start + 3]
        for column, name in zip(st.columns(len(row)), row):
            column.button(name, key=f"choice-{name}", on_click=queue_message, args=(name,))
else:
    next_field = missing_field(st.session_state.prefs)
    if next_field in QUICK_REPLIES:
        options = QUICK_REPLIES[next_field]
        for start in range(0, len(options), 5):          # rows of up to 5 buttons
            row = options[start:start + 5]
            for column, option in zip(st.columns(len(row)), row):
                column.button(option, key=f"{next_field}-{option}",
                              on_click=queue_message, args=(option,))