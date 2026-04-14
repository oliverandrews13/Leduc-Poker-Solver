from collections import namedtuple

DECK = ["J", "J", "Q", "Q", "K", "K"]
CARDS = ["J", "Q", "K"]
State = namedtuple("State", ["history", "p0_card", "p1_card", "board", "player"])

class LeducPoker:
    def is_terminal(self, state):
        if state.history.endswith("f"):
            return True

        if "/" in state.history:
            street_2 = state.history.split("/")[-1]
            # One-bet-per-street abstraction:
            # round ends on check-check, bet-call, or check-bet-call.
            if street_2 in {"cc", "bc", "cbc"}:
                return True
        return False

    def get_payoff(self, state):
        if state.history.endswith("f"):
            return 1 if state.player == 0 else -1
        
        def score(card, board):
            if card == board: return 10 + CARDS.index(card)
            return CARDS.index(card)
            
        p0 = score(state.p0_card, state.board)
        p1 = score(state.p1_card, state.board)
        return 1 if p0 > p1 else (-1 if p1 > p0 else 0)

    def get_legal_actions(self, state):
        active_hist = state.history.split("/")[-1]

        if active_hist in {"", "c"}:
            return ["c", "b"]

        if active_hist in {"b", "cb"}:
            return ["c", "f"]

        return []
