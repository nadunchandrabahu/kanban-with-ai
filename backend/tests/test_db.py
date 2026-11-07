from app import db


def test_init_db_seeds_default_user_and_board(temp_db_path):
    _ = temp_db_path
    db.init_db()
    assert db.verify_credentials("user", "password")
    board = db.get_board_for_user("user")
    assert len(board.columns) == 4
    assert "card-1" in board.cards


def test_save_and_load_board_round_trip(temp_db_path):
    _ = temp_db_path
    db.init_db()
    board = db.get_board_for_user("user")
    board.columns[0].title = "Ideas"
    db.save_board_for_user("user", board)
    reloaded = db.get_board_for_user("user")
    assert reloaded.columns[0].title == "Ideas"
