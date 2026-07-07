import streamlit as st
from engine.data_loader import load_json
from engine.mechanics import get_type_multiplier

st.title("Pokémon Battle Compass")

types = load_json("types")
team_data = load_json("team_data")

st.header("Type Effectiveness Test")

attack_type = st.selectbox("Attacking type", types)
defender_type_1 = st.selectbox("Defender Type 1", types)
defender_type_2 = st.selectbox("Defender Type 2", [""] + types)

multiplier = get_type_multiplier(
    attack_type,
    [defender_type_1, defender_type_2]
)

st.subheader("Result")
st.write(
    f"{attack_type} vs {defender_type_1}/{defender_type_2 or 'None'} = **{multiplier}x**"
)

st.divider()

st.header("Team Data Test")

pokemon_names = [
    pokemon["Pokemon"]
    for pokemon in team_data
]

selected_name = st.selectbox(
    "Choose a team Pokémon",
    pokemon_names
)

selected_pokemon = next(
    pokemon
    for pokemon in team_data
    if pokemon["Pokemon"] == selected_name
)

st.subheader(selected_pokemon["Pokemon"])

st.write(
    f"**Type:** {selected_pokemon['Type1']}"
    + (f" / {selected_pokemon['Type2']}" if selected_pokemon["Type2"] else "")
)

st.write(f"**Level:** {selected_pokemon['Level']}")
st.write(f"**Ability:** {selected_pokemon['Ability']}")
st.write(f"**Held Item:** {selected_pokemon['Held Item']}")

st.write("**Stats**")
st.dataframe({
    "Stat": ["HP", "ATK", "DEF", "SPA", "SPD", "SPE"],
    "Value": [
        selected_pokemon["HP"],
        selected_pokemon["ATK"],
        selected_pokemon["DEF"],
        selected_pokemon["SPA"],
        selected_pokemon["SPD"],
        selected_pokemon["SPE"],
    ]
})

st.write("**Moves**")
st.dataframe({
    "Move": [
        selected_pokemon["Move1"],
        selected_pokemon["Move2"],
        selected_pokemon["Move3"],
        selected_pokemon["Move4"],
    ],
    "Type": [
        selected_pokemon["Move1Type"],
        selected_pokemon["Move2Type"],
        selected_pokemon["Move3Type"],
        selected_pokemon["Move4Type"],
    ],
    "Power": [
        selected_pokemon["Move1Power"],
        selected_pokemon["Move2Power"],
        selected_pokemon["Move3Power"],
        selected_pokemon["Move4Power"],
    ],
    "Category": [
        selected_pokemon["Move1Category"],
        selected_pokemon["Move2Category"],
        selected_pokemon["Move3Category"],
        selected_pokemon["Move4Category"],
    ],
    "Accuracy": [
        selected_pokemon["Move1Accuracy"],
        selected_pokemon["Move2Accuracy"],
        selected_pokemon["Move3Accuracy"],
        selected_pokemon["Move4Accuracy"],
    ],
})