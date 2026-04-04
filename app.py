import streamlit as st
import numpy as np

# Import your CFR solver
from cfr import LeducCFR

st.set_page_config(page_title="Leduc Poker CFR Solver", layout="wide")

st.title("🃏 Leduc Poker CFR Solver")
st.write("Train a Counterfactual Regret Minimization (CFR) solver and inspect learned strategies.")

# Sidebar controls
st.sidebar.header("Training Settings")
iterations = st.sidebar.slider("Iterations", min_value=100, max_value=5000, value=1000, step=100)
log_every = st.sidebar.slider("Log Frequency", min_value=10, max_value=1000, value=100, step=10)

# Run button
if st.button("🚀 Run CFR Training"):
    with st.spinner("Training CFR solver..."):
        solver = LeducCFR()
        solver.train(iterations=iterations, log_every=log_every)

    st.success("Training complete!")

    # Display number of info sets
    st.subheader("Summary")
    st.write(f"Total info sets discovered: {len(solver.info_sets)}")

    # Display strategies
    st.subheader("Learned Strategies")

    for key in sorted(solver.info_sets.keys()):
        iset = solver.info_sets[key]
        avg_strategy = iset.get_average_strategy()

        with st.expander(f"Info Set: {key}"):
            actions = [f"Action {i}" for i in range(len(avg_strategy))]
            strategy_dict = {actions[i]: float(avg_strategy[i]) for i in range(len(avg_strategy))}
            st.write(strategy_dict)

    st.subheader("Regret Diagnostics")
    st.write("Regret sums (sample):")

    sample_keys = list(solver.info_sets.keys())[:5]
    for key in sample_keys:
        iset = solver.info_sets[key]
        st.write(f"{key}: {iset.regret_sum}")

else:
    st.info("Adjust settings and click 'Run CFR Training' to start.")
