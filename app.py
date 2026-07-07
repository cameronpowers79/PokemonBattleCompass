import streamlit as st
from engine.mechanics import get_type_multiplier

st.title("Pokémon Battle Compass")
st.write("Type effectiveness test")

attack_type = st.selectbox(
    "Attacking type",
    ["Normal", "Fire", "Water", "Electric", "Grass", "Ice",
    "Fighting", "Poison", "Ground", "Flying", "Psychic", "Bug",
    "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy"]
)

defender_type_1 = st.selectbox(
    "Defender Type 1",
    ["Normal", "Fire", "Water", "Electric", "Grass", "Ice",
    "Fighting", "Poison", "Ground", "Flying", "Psychic", "Bug",
    "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy"]
)

defender_type_2 = st.selectbox(
    "Defender Type 2",
    ["", "Normal", "Fire", "Water", "Electric", "Grass", "Ice",
    "Fighting", "Poison", "Ground", "Flying", "Psychic", "Bug",
    "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy"]
)

multiplier = get_type_multiplier(
    attack_type,
    [defender_type_1, defender_type_2]
)

st.subheader("Result")
st.write(f"{attack_type} vs {defender_type_1}/{defender_type_2 or 'None'} = **{multiplier}x**")