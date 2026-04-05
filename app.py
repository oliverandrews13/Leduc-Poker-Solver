import streamlit as st
import random
from collections import defaultdict
from leduc import LeducPoker, State, DECK, CARDS

ACTION_META = {
    "c": {"label": "Check / Call", "short": "C", "color": "#4aa3ff"},
    "b": {"label": "Bet", "short": "B", "color": "#ff6b6b"},
    "f": {"label": "Fold", "short": "F", "color": "#9aa4b2"},
}

ROUND_COMPLETE = {"cc", "bc", "cbc"}
TRAINING_ITERATIONS = 100000

# --- CFR SOLVER ENGINE ---
class CFRSolver:
    def __init__(self):
        self.game = LeducPoker()
        self.regret_sum = defaultdict(lambda: defaultdict(float))
        self.strategy_sum = defaultdict(lambda: defaultdict(float))
        self.ev_cache = {}

    def get_info_key(self, state):
        card = state.p0_card if state.player == 0 else state.p1_card
        return f"{card}|{state.board or '-'}|{state.history}"

    def get_strategy(self, key, actions, use_avg=False):
        d = self.strategy_sum[key] if use_avg else self.regret_sum[key]
        norm = sum(d.values()) if use_avg else sum(max(v, 0) for v in d.values())
        return {a: (d[a] if use_avg else max(d[a], 0)) / norm if norm > 0 else 1/len(actions) for a in actions}

    def expected_value(self, state, use_avg=True):
        cache_key = (state, use_avg)
        if cache_key in self.ev_cache:
            return self.ev_cache[cache_key]

        if self.game.is_terminal(state):
            value = self.game.get_payoff(state)
            self.ev_cache[cache_key] = value
            return value

        active_h = state.history.split("/")[-1]
        if state.board is None and active_h in ROUND_COMPLETE:
            ev = 0
            rem = DECK[:]
            rem.remove(state.p0_card)
            rem.remove(state.p1_card)
            for c in set(rem):
                prob = rem.count(c) / len(rem)
                child = state._replace(board=c, history=state.history + "/", player=0)
                ev += prob * self.expected_value(child, use_avg=use_avg)
            self.ev_cache[cache_key] = ev
            return ev

        actions = self.game.get_legal_actions(state)
        key = self.get_info_key(state)
        strat = self.get_strategy(key, actions, use_avg=use_avg)
        value = 0
        for action in actions:
            child = state._replace(history=state.history + action, player=1 - state.player)
            value += strat[action] * self.expected_value(child, use_avg=use_avg)
        self.ev_cache[cache_key] = value
        return value

    def action_evs(self, state, use_avg=True):
        actions = self.game.get_legal_actions(state)
        return {
            action: self.expected_value(
                state._replace(history=state.history + action, player=1 - state.player),
                use_avg=use_avg,
            )
            for action in actions
        }

    def cfr(self, state, p0, p1, iteration):
        if self.game.is_terminal(state):
            return self.game.get_payoff(state)

        # CHANCE NODE (Flop Transition)
        active_h = state.history.split("/")[-1]
        # Transition after a completed preflop betting round.
        if state.board is None and active_h in ROUND_COMPLETE:
            ev = 0
            rem = DECK[:]
            rem.remove(state.p0_card)
            rem.remove(state.p1_card)
            for c in set(rem):
                prob = rem.count(c) / len(rem)
                child = state._replace(board=c, history=state.history + "/", player=0)
                ev += prob * self.cfr(child, p0, p1, iteration)
            return ev

        key = self.get_info_key(state)
        actions = self.game.get_legal_actions(state)
        strat = self.get_strategy(key, actions)

        utils = {a: self.cfr(state._replace(history=state.history + a, player=1 - state.player), 
                            p0 * strat[a] if state.player == 0 else p0, 
                            p1 * strat[a] if state.player == 1 else p1, iteration) for a in actions}
        
        node_util = sum(strat[a] * utils[a] for a in actions)

        # Update Regret/Strategy with Linear Weighting
        reach_p, opp_p = (p0, p1) if state.player == 0 else (p1, p0)
        for a in actions:
            regret = (utils[a] - node_util) if state.player == 0 else (node_util - utils[a])
            self.regret_sum[key][a] += opp_p * regret
            self.strategy_sum[key][a] += iteration * reach_p * strat[a] 
        return node_util

    def train(self, iters):
        deals = [(DECK[i], DECK[j]) for i in range(6) for j in range(6) if i != j]
        for i in range(iters):
            self.cfr(State("", *random.choice(deals), None, 0), 1.0, 1.0, i)
        self.ev_cache.clear()

# --- STREAMLIT UI ---
st.set_page_config(page_title="Leduc GTO Wizard", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(49, 74, 111, 0.28), transparent 34%),
            linear-gradient(180deg, #0b1220 0%, #0f1726 100%);
        color: #e8eef7;
    }
    html, body, [class*="css"]  {
        font-family: "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f1726 0%, #111b2e 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    [data-testid="stMetricValue"] {
        color: #f7fbff;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1180px;
    }
    .panel {
        background: rgba(10, 16, 28, 0.84);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 1.1rem 1.15rem;
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25);
    }
    .hero {
        display: grid;
        grid-template-columns: 1.6fr 1fr;
        gap: 16px;
        margin-bottom: 1rem;
    }
    .hero-title {
        font-size: 2rem;
        font-weight: 650;
        letter-spacing: -0.03em;
        margin-bottom: 0.5rem;
    }
    .hero-subtitle {
        color: #9fb0c8;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .path-pill {
        display: inline-block;
        padding: 0.35rem 0.65rem;
        border-radius: 999px;
        background: rgba(74, 163, 255, 0.12);
        border: 1px solid rgba(74, 163, 255, 0.28);
        color: #d8ebff;
        font-size: 0.8rem;
        margin-top: 0.9rem;
    }
    .stat-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
    }
    .stat-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        padding: 0.85rem 0.95rem;
    }
    .stat-label {
        color: #8ea2bf;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.72rem;
    }
    .stat-value {
        color: #f7fbff;
        font-size: 1.2rem;
        font-weight: 640;
        margin-top: 0.2rem;
    }
    .section-label {
        font-size: 0.82rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #8ea2bf;
        margin: 1.4rem 0 0.8rem;
    }
    .action-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
        margin-bottom: 0.85rem;
    }
    .action-card {
        border-radius: 18px;
        padding: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
    }
    .action-head {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 0.75rem;
    }
    .action-name {
        font-size: 1rem;
        font-weight: 620;
    }
    .action-frequency {
        font-size: 1.35rem;
        font-weight: 680;
    }
    .action-ev {
        color: #b7c6d9;
        font-size: 0.86rem;
        margin-bottom: 0.7rem;
    }
    .mix-bar {
        display: flex;
        width: 100%;
        height: 10px;
        overflow: hidden;
        border-radius: 999px;
        background: rgba(255,255,255,0.06);
    }
    .mix-segment {
        height: 100%;
    }
    .matrix-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
        margin-top: 0.6rem;
    }
    .matrix-tile {
        aspect-ratio: 1 / 1;
        border-radius: 22px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(11, 18, 32, 0.94);
        padding: 0.95rem;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
    }
    .tile-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .tile-card {
        font-size: 1.6rem;
        font-weight: 700;
        letter-spacing: -0.04em;
    }
    .tile-best {
        font-size: 0.74rem;
        color: #8ea2bf;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .tile-ev {
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: -0.04em;
    }
    .tile-note {
        color: #8ea2bf;
        font-size: 0.82rem;
    }
    .tile-mix-list {
        display: grid;
        gap: 0.25rem;
        margin-top: 0.55rem;
        font-size: 0.8rem;
        color: #d7e3f2;
    }
    .tile-mix-row {
        display: flex;
        justify-content: space-between;
    }
    .street-panel {
        margin-top: 1rem;
        padding: 0.95rem 1rem;
        border-radius: 18px;
        background: rgba(14, 22, 37, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .stButton > button {
        width: 100%;
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: linear-gradient(180deg, #17243b 0%, #111b2d 100%);
        color: #edf5ff;
        font-weight: 600;
        min-height: 2.8rem;
    }
    .stSelectbox label, .stMarkdown p {
        color: #dce7f5;
    }
    @media (max-width: 900px) {
        .hero, .action-grid, .matrix-grid, .stat-grid {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def format_ev(ev):
    return f"{ev:+.2f}"


def player_view_ev(state, ev):
    return ev if state.player == 0 else -ev


def next_player_from_history(history):
    active_history = history.split("/")[-1]
    return len(active_history) % 2


def build_mix_bar(strategy):
    segments = []
    for action, freq in strategy.items():
        color = ACTION_META[action]["color"]
        width = max(freq * 100, 0)
        segments.append(
            f"<div class='mix-segment' style='width:{width:.2f}%; background:{color};'></div>"
        )
    return "<div class='mix-bar'>" + "".join(segments) + "</div>"


def build_action_card(action, frequency, ev):
    meta = ACTION_META[action]
    return f"""
    <div class="action-card">
        <div class="action-head">
            <div class="action-name" style="color:{meta['color']};">{meta['label']}</div>
            <div class="action-frequency">{frequency * 100:.1f}%</div>
        </div>
        <div class="action-ev">EV {format_ev(ev)}</div>
        <div class="mix-bar">
            <div class="mix-segment" style="width:{frequency * 100:.2f}%; background:{meta['color']};"></div>
        </div>
    </div>
    """


def build_range_tile(card, strategy, ev, best_action):
    best_label = ACTION_META[best_action]["short"] if best_action else "-"
    mix_rows = "".join(
        [
            (
                f"<div class='tile-mix-row'>"
                f"<span style='color:{ACTION_META[action]['color']};'>{ACTION_META[action]['label']}</span>"
                f"<span>{freq * 100:.0f}%</span>"
                f"</div>"
            )
            for action, freq in strategy.items()
        ]
    )
    return f"""
    <div class="matrix-tile">
        <div>
            <div class="tile-top">
                <div class="tile-card">{card}</div>
                <div class="tile-best">Best {best_label}</div>
            </div>
            <div class="tile-ev">{format_ev(ev)}</div>
            <div class="tile-note">Average node EV</div>
        </div>
        <div>
            {build_mix_bar(strategy)}
            <div class="tile-mix-list">{mix_rows}</div>
        </div>
    </div>
    """

@st.cache_resource
def get_trained_wizard():
    s = CFRSolver()
    with st.spinner(f"Solving Game... ({TRAINING_ITERATIONS:,} iterations)"):
        s.train(TRAINING_ITERATIONS)
    return s

wiz = get_trained_wizard()

if "history" not in st.session_state: st.session_state.history = ""
if "board" not in st.session_state: st.session_state.board = None

with st.sidebar:
    st.markdown("### Leduc Solver")
    st.caption("Clean node view with action mixes and hand tiles.")
    p0 = st.selectbox("Player 0 card", CARDS, index=0)
    p1 = st.selectbox("Player 1 card", CARDS, index=1)
    if st.button("Reset Tree"):
        st.session_state.history = ""; st.session_state.board = None; st.rerun()

# Transition Logic
active_h = st.session_state.history.split("/")[-1]
is_r1_over = active_h in ROUND_COMPLETE
if is_r1_over and "/" not in st.session_state.history:
    st.markdown(
        """
        <div class="street-panel">
            <div class="section-label" style="margin-top:0;">Street Transition</div>
            <div style="font-size:1.1rem; font-weight:620; margin-bottom:0.35rem;">Preflop complete</div>
            <div style="color:#9fb0c8;">Choose the board card to continue into the second street.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    b_card = st.selectbox("Reveal board", CARDS)
    if st.button("Confirm Flop"):
        st.session_state.board = b_card
        st.session_state.history += "/"
        st.rerun()
    st.stop()

# Strategy Lookup
player = next_player_from_history(st.session_state.history)
curr_state = State(st.session_state.history, p0, p1, st.session_state.board, player)
terminal = wiz.game.is_terminal(curr_state)
path_display = st.session_state.history.replace("/", " | ") or "Root"
street = "Flop" if st.session_state.board else "Preflop"
hero_card = curr_state.p0_card if player == 0 else curr_state.p1_card
villain_card = curr_state.p1_card if player == 0 else curr_state.p0_card
node_ev_raw = wiz.expected_value(curr_state, use_avg=True)
node_ev = player_view_ev(curr_state, node_ev_raw)

if terminal:
    actions = []
    strategy = {}
    action_evs = {}
    best_action = None
else:
    key = wiz.get_info_key(curr_state)
    actions = wiz.game.get_legal_actions(curr_state)
    strategy = wiz.get_strategy(key, actions, use_avg=True)
    action_evs = {
        action: player_view_ev(curr_state, ev)
        for action, ev in wiz.action_evs(curr_state, use_avg=True).items()
    }
    best_action = max(action_evs, key=action_evs.get)

hero_html = f"""
<div class="hero">
    <div class="panel">
        <div class="hero-title">Leduc Solver Board</div>
        <div class="hero-subtitle">
            Solver-style node view for the current decision point. The action cards show the mixed strategy
            for this exact state, and the hand tiles below approximate the EV-square feel by showing how each
            possible private card wants to play this node.
        </div>
        <div class="path-pill">Path: {path_display}</div>
    </div>
    <div class="panel">
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-label">Street</div>
                <div class="stat-value">{street}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Acting Player</div>
                <div class="stat-value">Player {player}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Hero Card</div>
                <div class="stat-value">{hero_card}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Board</div>
                <div class="stat-value">{st.session_state.board or "-"}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Node EV</div>
                <div class="stat-value">{format_ev(node_ev)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Opponent Card</div>
                <div class="stat-value">{villain_card}</div>
            </div>
        </div>
    </div>
</div>
"""
st.markdown(hero_html, unsafe_allow_html=True)

if terminal:
    st.markdown(
        f"""
        <div class="panel">
            <div class="section-label" style="margin-top:0;">Terminal Node</div>
            <div style="font-size:1.25rem; font-weight:650;">Hand complete</div>
            <div style="color:#9fb0c8; margin-top:0.35rem;">
                Realized payoff from the acting player's perspective: {format_ev(node_ev)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown('<div class="section-label">Action Mix</div>', unsafe_allow_html=True)
    action_cols = st.columns(len(actions))
    for idx, action in enumerate(actions):
        with action_cols[idx]:
            st.markdown(
                build_action_card(action, strategy[action], action_evs[action]),
                unsafe_allow_html=True,
            )

    button_cols = st.columns(len(actions))
    for idx, action in enumerate(actions):
        if button_cols[idx].button(ACTION_META[action]["label"], key=f"btn_{action}"):
            st.session_state.history += action
            st.rerun()

st.markdown('<div class="section-label">Range View</div>', unsafe_allow_html=True)
range_tiles = []
for card in CARDS:
    tile_state = (
        State(st.session_state.history, card, p1, st.session_state.board, player)
        if player == 0
        else State(st.session_state.history, p0, card, st.session_state.board, player)
    )
    tile_terminal = wiz.game.is_terminal(tile_state)
    tile_ev = player_view_ev(tile_state, wiz.expected_value(tile_state, use_avg=True))
    if tile_terminal:
        tile_strategy = {"c": 1.0}
        tile_best_action = "c"
    else:
        tile_actions = wiz.game.get_legal_actions(tile_state)
        tile_key = wiz.get_info_key(tile_state)
        tile_strategy = wiz.get_strategy(tile_key, tile_actions, use_avg=True)
        tile_action_evs = {
            action: player_view_ev(tile_state, ev)
            for action, ev in wiz.action_evs(tile_state, use_avg=True).items()
        }
        tile_best_action = max(tile_action_evs, key=tile_action_evs.get)
    range_tiles.append(build_range_tile(card, tile_strategy, tile_ev, tile_best_action))

range_cols = st.columns(len(range_tiles))
for idx, tile in enumerate(range_tiles):
    with range_cols[idx]:
        st.markdown(tile, unsafe_allow_html=True)
