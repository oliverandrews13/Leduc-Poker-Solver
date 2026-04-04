import streamlit as st
import numpy as np

from cfr import LeducCFR
from ui_bridge import SolverInterface

# =========================
# LOAD SOLVER
# =========================

@st.cache_resource
def load_solver():
    solver = LeducCFR()
    solver.train(iterations=500)
    return SolverInterface(solver)

interface = load_solver()

# =========================
# STATE MODEL
# =========================

if "history" not in st.session_state:
    st.session_state.history = []

if "board" not in st.session_state:
    st.session_state.board = "-"

# =========================
# SIDEBAR (SETUP)
# =========================

st.sidebar.header("Game Setup")

player = st.sidebar.selectbox("Player to Act", [0, 1])
private_card = st.sidebar.selectbox("Your Card", ["J", "Q", "K"])

if st.sidebar.button("Reset Hand"):
    st.session_state.history = []
    st.session_state.board = "-"

board_choice = st.sidebar.selectbox("Board Card (optional)", ["-", "J", "Q", "K"])

if st.sidebar.button("Set Board"):
    st.session_state.board = board_choice

# =========================
# BUILD HISTORY STRING
# =========================

history_str = "".join(st.session_state.history)

# =========================
# QUERY SOLVER
# =========================

result = interface.query(
    player,
    private_card,
    st.session_state.board,
    history_str
)

# =========================
# HEADER
# =========================

st.title("🧠 Leduc GTO Solver")

# =========================
# BREADCRUMB NAVIGATION
# =========================

st.subheader("Line")

cols = st.columns(len(st.session_state.history) + 1)

for i in range(len(st.session_state.history)):
    with cols[i]:
        if st.button(st.session_state.history[i], key=f"step_{i}"):
            st.session_state.history = st.session_state.history[:i]
            st.rerun()

with cols[-1]:
    st.write("⟶ Current")

st.write("---")

# =========================
# CURRENT STATE DISPLAY
# =========================

col1, col2, col3 = st.columns(3)

col1.metric("Player", player)
col2.metric("Card", private_card)
col3.metric("Board", st.session_state.board)

st.write("**History:**", history_str if history_str else "—")

# =========================
# STRATEGY + EV DISPLAY
# =========================

if result:
    actions = result["actions"]
    strategy = result["strategy"]

    st.subheader("Strategy")

    for a, p in zip(actions, strategy):
        label = {"c": "Check/Call", "b": "Bet/Raise", "f": "Fold"}.get(a, a)
        st.write(f"**{label}** → {p:.2f}")

    # Highlight best action
    best_idx = int(np.argmax(strategy))
    best_action = actions[best_idx]

    st.success(f"Recommended: {best_action}")

# =========================
# ACTION BUTTONS
# =========================

st.subheader("Actions")

if result:
    actions = result["actions"]

    cols = st.columns(len(actions))

    for i, a in enumerate(actions):
        label = {"c": "Check/Call", "b": "Bet/Raise", "f": "Fold"}.get(a, a)

        with cols[i]:
            if st.button(label, key=f"action_{a}_{i}"):
                st.session_state.history.append(a)
                st.rerun()

# =========================
# DEBUG
# =========================

with st.expander("Debug"):
    st.write("History List:", st.session_state.history)
    st.write("History String:", history_str)