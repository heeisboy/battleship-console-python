import importlib.util
from pathlib import Path
import unittest


def load_main_module():
    root = Path(__file__).resolve().parents[1]
    main_path = root / "morskoi-boi" / "main.py"
    spec = importlib.util.spec_from_file_location("morskoi_boi_main", main_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MAIN = load_main_module()
Board = MAIN.Board
Game = MAIN.Game
HumanPlayer = MAIN.HumanPlayer


class DummyUI:
    def say(self, message):
        pass

    def prompt(self, message):
        return ""

    def greet(self):
        pass

    def show_boards(self, user_board, ai_board):
        pass

    def announce_turn(self, user_turn):
        pass

    def show_winner(self, winner):
        pass

    def show_pvp_boards(self, left_board, right_board, left_name, right_name):
        pass


class GameConfigTests(unittest.TestCase):
    def test_win_count_uses_ships_config(self):
        game = Game(size=6, ships_config=[2, 1, 1], ui=DummyUI())
        self.assertEqual(game.win_count, 3)

        board = Board(size=6)
        board.count = 3
        self.assertTrue(game.is_winner(board))

        board.count = 2
        self.assertFalse(game.is_winner(board))

    def test_random_board_creates_expected_ship_count(self):
        config = [2, 1, 1]
        game = Game(size=6, ships_config=config, ui=DummyUI())
        board = game.random_board()
        self.assertEqual(len(board.ships), len(config))

    def test_pvp_mode_uses_humans_only(self):
        game = Game(size=6, ships_config=[1], ui=DummyUI(), mode="pvp")
        self.assertIsNone(game.ai)
        self.assertIsNone(game.us)
        self.assertIsInstance(game.p1, HumanPlayer)
        self.assertIsInstance(game.p2, HumanPlayer)

    def test_pvp_show_hides_enemy(self):
        calls = []

        class ProbeUI(DummyUI):
            def show_pvp_boards(self, left_board, right_board, left_name, right_name):
                calls.append(right_board.hid)

        game = Game(size=6, ships_config=[1], ui=ProbeUI(), mode="pvp")
        game._show_pvp_boards(game.p1, game.p2)
        self.assertEqual(calls, [True])


if __name__ == "__main__":
    unittest.main()
