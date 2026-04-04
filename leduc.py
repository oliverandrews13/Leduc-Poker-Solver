"""
Leduc Hold'em Game Logic
========================
2-player, 6-card deck: {J, Q, K} x 2 suits
- Both players ante 1 chip
- Round 1: private cards dealt, betting (bet=2, max 1 raise)
- Board card dealt
- Round 2: betting (bet=4, max 1 raise)
- Showdown: pair with board > high card
"""

# ── Cards ──────────────────────────────────────────────────────────────────────

RANKS = ['J', 'Q', 'K']
RANK_ORDER = {r: i for i, r in enumerate(RANKS)}   # J=0, Q=1, K=2
DECK = RANKS * 2                                    # 6-card deck

# ── Betting constants ──────────────────────────────────────────────────────────

ANTE        = 1
BET_R1      = 2   # round 1 bet/raise size
BET_R2      = 4   # round 2 bet/raise size
MAX_RAISES  = 1   # max raises per round

# ── Actions ────────────────────────────────────────────────────────────────────

FOLD  = 'f'
CALL  = 'c'   # also acts as CHECK when no bet is outstanding
BET   = 'b'   # also acts as RAISE when a bet is already out

ACTIONS = [FOLD, CALL, BET]


# ── History helpers ────────────────────────────────────────────────────────────

def get_round(history: str) -> int:
    """0 = pre-board, 1 = post-board."""
    return 1 if '/' in history else 0


def current_round_history(history: str) -> str:
    """Actions in the current round only."""
    return history.split('/')[-1]


def get_bet_size(history: str) -> int:
    return BET_R2 if get_round(history) == 1 else BET_R1


def raises_this_round(history: str) -> int:
    """Count raises (BET actions) in the current round."""
    return current_round_history(history).count(BET)


def bet_outstanding(history: str) -> bool:
    """True if the last action in this round is a BET (facing a bet/raise)."""
    rh = current_round_history(history)
    if not rh:
        return False
    return rh[-1] == BET


def get_legal_actions(history: str) -> list[str]:
    """Return list of legal actions from the current state."""
    actions = [CALL]                                # can always check/call
    if bet_outstanding(history):
        actions.append(FOLD)                        # can only fold facing a bet
    if raises_this_round(history) < MAX_RAISES:
        actions.append(BET)
    return actions


# ── Terminal detection ─────────────────────────────────────────────────────────

def is_terminal(history: str) -> bool:
    """Return True if the hand is over."""
    rh = current_round_history(history)
    round_n = get_round(history)

    # Fold ends the hand immediately
    if rh.endswith(FOLD):
        return True

    # Round ends on check-check (cc) or call-after-bet (bc or bbc... actually bc)
    # In round 0: first to act can check (c) or bet (b)
    # Round ends if:
    #   - "cc"   → both checked
    #   - "bc"   → bet then called
    #   - "bbc"  → bet, raise, called  (but MAX_RAISES=1 so "bbc" is max)
    #   - after a call following a bet, if that closes the round

    if round_n == 0:
        # Round 1 done → go to round 2 (marked by '/')
        # Treated as terminal only after round 2 completes
        return False

    # Round 2 terminal conditions (same logic)
    if rh == 'cc':
        return True
    if rh.endswith(CALL) and BET in rh:
        return True

    return False


def is_chance_node(history: str) -> bool:
    """True when we need to deal the board card (transition between rounds)."""
    if get_round(history) == 1:
        return False
    rh = current_round_history(history)
    # Round 1 ends: cc, or bc, or bbc (with MAX_RAISES=1 that's just bc)
    if rh == 'cc':
        return True
    if rh.endswith(CALL) and BET in rh:
        return True
    return False


# ── Whose turn ─────────────────────────────────────────────────────────────────

def acting_player(history: str) -> int:
    """Return 0 or 1 — who acts next. Player 0 acts first in both rounds."""
    rh = current_round_history(history)
    return len(rh) % 2   # alternating: 0 acts on even counts, 1 on odd


# ── Pot calculation ────────────────────────────────────────────────────────────

def compute_pot(history: str) -> tuple[int, int]:
    """
    Return (pot_p0, pot_p1) — total chips each player has put in.
    Both start at ANTE=1.
    """
    p = [ANTE, ANTE]

    rounds = history.split('/')
    for r_idx, rh in enumerate(rounds):
        bet_size = BET_R2 if r_idx == 1 else BET_R1
        facing_bet = False
        current_bet = 0
        actor = 0

        for action in rh:
            if action == BET:
                if not facing_bet:
                    current_bet = bet_size
                else:
                    current_bet += bet_size   # raise
                p[actor] += bet_size
                facing_bet = True
            elif action == CALL:
                if facing_bet:
                    p[actor] += current_bet - (p[actor] - ANTE - _prev_invested(rh[:rh.index(action)], r_idx))
                    # Simplified: just add the call amount
                    pass
                # (handled below with simpler approach)
            actor = 1 - actor

    # Simpler recalculation: replay action by action
    return _replay_pot(history)


def _replay_pot(history: str) -> tuple[int, int]:
    """Clean pot replay."""
    p = [ANTE, ANTE]
    rounds = history.split('/')

    for r_idx, rh in enumerate(rounds):
        bet_size = BET_R2 if r_idx == 1 else BET_R1
        actor = 0
        round_invested = [0, 0]
        max_invested = 0

        for action in rh:
            if action == BET:
                # Bet or raise to (max_invested + bet_size)
                new_level = max_invested + bet_size
                diff = new_level - round_invested[actor]
                p[actor] += diff
                round_invested[actor] = new_level
                max_invested = new_level
            elif action == CALL:
                diff = max_invested - round_invested[actor]
                p[actor] += diff
                round_invested[actor] = max_invested
            # FOLD: no chip movement
            actor = 1 - actor

    return tuple(p)


def _prev_invested(rh_prefix: str, r_idx: int) -> int:
    """Helper — not used in final version."""
    return 0


# ── Hand evaluation ────────────────────────────────────────────────────────────

def hand_rank(private: str, board: str) -> int:
    """
    Higher is better.
    Pair with board = 10 + rank_value
    High card       = rank_value
    """
    if private == board:
        return 10 + RANK_ORDER[private]
    return RANK_ORDER[private]


# ── Payoff ─────────────────────────────────────────────────────────────────────

def get_payoff(history: str, cards: list[str]) -> int:
    """
    Return payoff for player 0 at a terminal node.
    cards = [p0_card, p1_card, board_card]
    Positive = p0 wins, Negative = p0 loses.
    """
    assert is_terminal(history), f"Not a terminal node: {history}"

    p0_card, p1_card, board_card = cards
    pot_p0, pot_p1 = _replay_pot(history)
    total_pot = pot_p0 + pot_p1

    rh = current_round_history(history)

    # Fold: whoever folded loses their investment
    if rh.endswith(FOLD):
        # acting_player(history) = next to act, so the one who just folded = opposite
        folder = 1 - acting_player(history)
        if folder == 0:
            return -pot_p0          # p0 folded, loses what they put in
        else:
            return pot_p1           # p1 folded, p0 wins pot_p1

    # Showdown
    r0 = hand_rank(p0_card, board_card)
    r1 = hand_rank(p1_card, board_card)

    if r0 > r1:
        return pot_p1      # p0 wins p1's chips
    elif r1 > r0:
        return -pot_p0     # p1 wins p0's chips
    else:
        return 0           # chop


# ── Info set key ───────────────────────────────────────────────────────────────

def info_set_key(player: int, private_card: str, board_card: str | None, history: str) -> str:
    """
    Unique key for an information set.
    player sees: their private card, the board card (if dealt), and full history.
    """
    board_str = board_card if board_card else '-'
    return f"{player}|{private_card}|{board_str}|{history}"


# ── Quick sanity test ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== Leduc Hold'em Game Logic ===\n")

    # Test hand ranks
    print("Hand ranks:")
    for r in RANKS:
        for b in RANKS:
            print(f"  private={r}, board={b}: rank={hand_rank(r, b)}")

    print()

    # Test legal actions
    for hist in ['', 'b', 'bb', 'bc', 'c']:
        print(f"  history='{hist}' → legal={get_legal_actions(hist)}, "
              f"terminal={is_terminal(hist)}, chance={is_chance_node(hist)}, "
              f"actor={acting_player(hist)}")

    print()

    # Test payoffs
    # p0 folds preflop
    h = 'f'
    cards = ['K', 'J', 'Q']
    pot = _replay_pot(h)
    print(f"history='{h}', cards={cards}: pot={pot}, payoff={get_payoff(h, cards)}")

    # p1 folds after p0 bets
    h = 'bf'
    cards = ['K', 'J', 'Q']
    pot = _replay_pot(h)
    print(f"history='{h}', cards={cards}: pot={pot}, payoff={get_payoff(h, cards)}")

    # Showdown after round 2 check-check
    h = 'cc/cc'
    cards = ['K', 'J', 'Q']
    pot = _replay_pot(h)
    print(f"history='{h}', cards={cards}: pot={pot}, payoff={get_payoff(h, cards)}")

    # Pair for p0
    h = 'cc/cc'
    cards = ['Q', 'J', 'Q']
    pot = _replay_pot(h)
    print(f"history='{h}', cards={cards}: pot={pot}, payoff={get_payoff(h, cards)}")
