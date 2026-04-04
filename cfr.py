"""
Leduc Hold'em CFR Solver
========================
Vanilla Counterfactual Regret Minimization.
Run this file directly to train and print the Nash equilibrium strategy.
"""

import random
from itertools import permutations
from collections import defaultdict
import numpy as np

from leduc import (
    DECK, RANKS, ACTIONS,
    get_legal_actions, is_terminal, is_chance_node,
    acting_player, get_payoff, info_set_key,
    _replay_pot, hand_rank
)

# ── Info Set ───────────────────────────────────────────────────────────────────

class InfoSet:
    def __init__(self, n_actions: int):
        self.regret_sum   = np.zeros(n_actions)
        self.strategy_sum = np.zeros(n_actions)
        self.n_actions    = n_actions

    def get_strategy(self, reach_prob: float) -> np.ndarray:
        """Regret-match to get current strategy, accumulate weighted average."""
        pos_regret = np.maximum(self.regret_sum, 0)
        total = pos_regret.sum()
        if total > 0:
            strategy = pos_regret / total
        else:
            strategy = np.ones(self.n_actions) / self.n_actions
        self.strategy_sum += reach_prob * strategy
        return strategy

    def get_average_strategy(self) -> np.ndarray:
        """The average strategy converges to Nash as iterations → ∞."""
        total = self.strategy_sum.sum()
        if total > 0:
            return self.strategy_sum / total
        return np.ones(self.n_actions) / self.n_actions


# ── CFR Solver ─────────────────────────────────────────────────────────────────

class LeducCFR:
    def __init__(self):
        self.info_sets: dict[str, InfoSet] = {}

    def get_info_set(self, key: str, n_actions: int) -> InfoSet:
        if key not in self.info_sets:
            self.info_sets[key] = InfoSet(n_actions)
        else:
            assert self.info_sets[key].n_actions == n_actions, (
                f"Info set '{key}' created with {self.info_sets[key].n_actions} actions "
                f"but now called with {n_actions}"
            )
        return self.info_sets[key]

    def cfr(
        self,
        history: str,
        cards: list[str],          # [p0_card, p1_card, board_card_or_None]
        reach_probs: np.ndarray,   # [pi_0, pi_1] — reach probability for each player
    ) -> float:
        """
        Recursive CFR traversal.
        Returns the expected value for player 0.
        """

        # ── Terminal node ──────────────────────────────────────────────────────
        if is_terminal(history):
            return get_payoff(history, cards)

        # ── Chance node: deal board card ───────────────────────────────────────
        if is_chance_node(history):
            return self._handle_chance(history, cards, reach_probs)

        # ── Player node ────────────────────────────────────────────────────────
        player   = acting_player(history)
        board    = cards[2]
        legal    = get_legal_actions(history)
        n        = len(legal)

        key      = info_set_key(player, cards[player], board, history)
        iset     = self.get_info_set(key, n)
        strategy = iset.get_strategy(reach_probs[player])

        # Recurse over each action
        action_values = np.zeros(n)
        for i, action in enumerate(legal):
            new_history = history + action

            # Update reach probabilities
            new_reach = reach_probs.copy()
            new_reach[player] *= strategy[i]

            action_values[i] = self.cfr(new_history, cards, new_reach)

        # Expected value under current strategy (always from p0 perspective)
        node_value = float(strategy @ action_values)

        # Update regrets — counterfactual weight is opponent's reach prob
        # For p1, action_values are from p0's perspective, so negate for p1's regret
        opponent  = 1 - player
        cf_weight = reach_probs[1 - player]
        iset.regret_sum += reach_probs[1 - player] * (action_values - node_value)

        return node_value

    def _handle_chance(
        self,
        history: str,
        cards: list[str],
        reach_probs: np.ndarray,
    ) -> float:
        """
        Average over all possible board cards (excluding dealt private cards).
        Board card is equally likely to be any remaining card.
        """
        used       = [cards[0], cards[1]]          # private cards already dealt
        remaining  = list(DECK)
        for c in used:
            remaining.remove(c)                    # remove one copy

        total_value = 0.0
        for board_card in set(remaining):          # unique ranks to avoid double-counting
            # Count how many copies of this rank remain
            count     = remaining.count(board_card)
            prob      = count / len(remaining)
            new_cards = [cards[0], cards[1], board_card]
            new_hist  = history + '/' 
            total_value += prob * self.cfr(new_hist, new_cards, reach_probs)

        return total_value

    def train(self, iterations: int = 10_000, log_every: int = 1_000):
        """
        Train by iterating over all possible private card deals.
        For Leduc (6-card deck, 2 players), there are 6×5 = 30 ordered deals.
        We weight each by its probability (1/30) and run CFR.
        """
        print(f"Training for {iterations:,} iterations...\n")

        for it in range(1, iterations + 1):
            # Enumerate all ordered (p0_card, p1_card) pairs and average
            total_ev = 0.0
            deal_count = 0

            deck = list(DECK)
            for p0_card in set(deck):
                deck_after_p0 = list(deck)
                deck_after_p0.remove(p0_card)
                for p1_card in set(deck_after_p0):
                    # Weight by probability of this deal
                    p0_count = deck.count(p0_card)
                    p1_count = deck_after_p0.count(p1_card)
                    prob = (p0_count / len(deck)) * (p1_count / len(deck_after_p0))

                    cards = [p0_card, p1_card, None]
                    ev    = self.cfr('', cards, np.ones(2))
                    total_ev   += prob * ev
                    deal_count += 1

            if it % log_every == 0 or it == 1:
                print(f"  Iteration {it:>6,} | EV(p0) ≈ {total_ev:+.4f} | Info sets: {len(self.info_sets)}")

        print(f"\nDone. Total info sets: {len(self.info_sets)}")


# ── Strategy display ───────────────────────────────────────────────────────────

def print_strategy(solver: LeducCFR):
    """Print the average (Nash) strategy for every info set."""
    print("\n=== Nash Equilibrium Strategy ===\n")
    print(f"{'Info Set Key':<35} {'Actions':<20} Strategy")
    print("-" * 75)

    for key in sorted(solver.info_sets.keys()):
        iset    = solver.info_sets[key]
        avg     = iset.get_average_strategy()
        legal   = get_legal_actions_from_key(key)
        action_str = "/".join(legal)
        prob_str   = "  ".join(f"{a}:{p:.3f}" for a, p in zip(legal, avg))
        print(f"  {key:<33} [{action_str:<6}]  {prob_str}")


def get_legal_actions_from_key(key: str) -> list[str]:
    """Re-derive legal actions from an info set key."""
    # key format: "player|private|board|history"
    parts   = key.split('|')
    history = parts[3]
    return get_legal_actions(history)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    solver = LeducCFR()
    solver.train(iterations=1_000, log_every=100)
    print_strategy(solver)
