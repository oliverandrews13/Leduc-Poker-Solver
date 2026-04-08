This project is a Python-based implementation of Counterfactual Regret Minimization (CFR) applied to Leduc Hold’em, a simplified poker variant commonly used to test game-theoretic algorithms.

The solver models imperfect-information gameplay and iteratively approximates a Nash equilibrium strategy by minimizing regret over repeated self-play. It handles chance events (card dealing), hidden information, and sequential decision-making, making it a useful framework for studying equilibrium computation in zero-sum games.

Key Features:
Implementation of vanilla CFR with regret matching
Support for imperfect-information game trees
Handling of chance nodes (card dealing) via probabilistic sampling
Computation of average strategies that converge toward Nash equilibrium
Exploitability measurement to evaluate strategy quality
Structured modular design separating game logic (leduc.py) and solver (cfr.py)
Purpose:

The project serves as a foundational step toward building more advanced poker solvers (e.g., no-limit Texas Hold’em agents like DeepStack-style systems) by validating core equilibrium-solving techniques in a tractable environment.
