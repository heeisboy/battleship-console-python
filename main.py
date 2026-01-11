from battleship.game import Game
from battleship.ui_console import ConsoleUI


def main():
    ui = ConsoleUI()
    mode = ui.choose_game_mode()
    size, ships_config = ui.choose_game_settings()
    game = Game(size=size, ships_config=ships_config, ui=ui, mode=mode)
    game.start()


if __name__ == "__main__":
    main()
