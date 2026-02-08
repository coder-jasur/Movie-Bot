from aiogram.fsm.state import State, StatesGroup


class AdminMenuSG(StatesGroup):
    menu = State()
    statistics = State()
    broadcast_input = State()
    broadcast_confirm = State()


class BackupSG(StatesGroup):
    menu = State()


class AddMovieWizardSG(StatesGroup):
    choose_type = State()
    input_code = State()
    quick_add = State()
    input_name = State()
    input_series_number = State()
    input_season_number = State()
    input_file = State()
    input_caption = State()
    select_genres = State()  # Genre selection
    confirm = State()     # The Hub (Video + Info + Save/Edit/Cancel)
    edit_menu = State()   # Choose which field to edit
    edit_field = State()  # Actually input the new value for a specific field
    success = State()     # Loop/Finish


class EditMovieSG(StatesGroup):
    input_code = State()
    select_action = State() # Menu: Edit Name, Caption, File, Delete, Code, Eps
    edit_name = State()
    edit_caption = State()
    edit_file = State()
    edit_code = State()
    edit_genres = State()  # Genre editing
    confirm_delete = State()

    # Episode management
    select_season = State()
    select_episode = State()
    edit_episode_details = State() # Sub-menu for a specific episode
    edit_season_num = State()
    edit_episode_num = State()
    confirm_delete_episode = State()
    confirm_delete_season = State()
    edit_global_season = State()
