TYPE_COLORS = {
    "Normal": "#A8A77A",
    "Fire": "#EE8130",
    "Water": "#6390F0",
    "Electric": "#F7D02C",
    "Grass": "#7AC74C",
    "Ice": "#96D9D6",
    "Fighting": "#C22E28",
    "Poison": "#A33EA1",
    "Ground": "#E2BF65",
    "Flying": "#A98FF3",
    "Psychic": "#F95587",
    "Bug": "#A6B91A",
    "Rock": "#B6A136",
    "Ghost": "#735797",
    "Dragon": "#6F35FC",
    "Dark": "#705746",
    "Steel": "#B7B7CE",
    "Fairy": "#D685AD",
}


def render_type_badges(types):
    badges = []

    for pokemon_type in types:
        if not pokemon_type:
            continue

        color = TYPE_COLORS.get(pokemon_type, "#777777")

        badges.append(
            f"""
            <span style="
                background-color: {color};
                color: white;
                padding: 4px 10px;
                border-radius: 999px;
                font-size: 0.85rem;
                font-weight: 700;
                margin-right: 6px;
                display: inline-block;
                min-width: 64px;
                text-align: center;
                text-shadow: 0 1px 1px rgba(0,0,0,.35);
            ">
                {pokemon_type}
            </span>
            """
        )

    st.markdown("".join(badges), unsafe_allow_html=True)