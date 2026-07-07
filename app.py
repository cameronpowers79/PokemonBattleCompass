import streamlit as st
from engine.data_loader import load_json
from engine.mechanics import get_type_multiplier

st.title("Pokémon Battle Compass")
st.write("Type effectiveness test")

types = load_json("types")

attack_type = st.selectbox(
    "Attacking type",
    types
)

defender_type_1 = st.selectbox(
    "Defender Type 1",
    types
)

defender_type_2 = st.selectbox(
    "Defender Type 2",
    [""] + types
)

multiplier = get_type_multiplier(
    attack_type,
    [defender_type_1, defender_type_2]
)

st.subheader("Result")
st.write(f"{attack_type} vs {defender_type_1}/{defender_type_2 or 'None'} = **{multiplier}x**")