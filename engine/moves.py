'''engine/moves.py'''

def get_move_metadata(move_name, moves_data):
    for move in moves_data:
        if move.get("Move") == move_name:
            return move

    return None


def apply_move_metadata(pokemon, moves_data):
    for slot in range(1, 5):
        move_name = pokemon.get(f"Move{slot}")
        move = get_move_metadata(move_name, moves_data)

        if not move:
            continue

        pokemon[f"Move{slot}Type"] = move.get("Type")
        pokemon[f"Move{slot}Power"] = move.get("Power")
        pokemon[f"Move{slot}Category"] = move.get("Category")
        pokemon[f"Move{slot}Accuracy"] = move.get("Accuracy")

    return pokemon