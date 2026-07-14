## Terminal Commands and code for dev testing


# Restore Team Cameron (default .json team_data)
    In flet_app.py, Immediately after:

    await app_state.initialize()

    temporarily add:

    # TEMPORARY: Restore Team Cameron into Journey storage.
    await app_state.start_new_journey("Scorbunny")
    await app_state.save_team(
        reference_data["team_data"]
    )

# Normalize Textures
    python tools/normalize_textures.py 

