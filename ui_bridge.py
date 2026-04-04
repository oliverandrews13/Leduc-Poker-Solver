from leduc import get_legal_actions
from cfr import LeducCFR  # rename this

class SolverInterface:
    def __init__(self, solver):
        self.solver = solver

    def query(self, player, private_card, board_card, history):
        key = f"{player}|{private_card}|{board_card}|{history}"
        iset = self.solver.info_sets.get(key, None)

        if iset is None:
            return None

        strategy = iset.get_average_strategy()
        actions = get_legal_actions(history)

        return {
            "key": key,
            "actions": actions,
            "strategy": strategy
        }