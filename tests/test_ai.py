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
Dot = MAIN.Dot
Ship = MAIN.Ship
Board = MAIN.Board
AI = MAIN.AI


class DummyUI:
    def say(self, message):
        pass

    def prompt(self, message):
        return ""


def prefer_dot(preferred):
    def _choice(dots):
        for d in dots:
            if d == preferred:
                return d
        return dots[0]
    return _choice


def build_enemy_board(bow, length, orientation=0, size=6):
    board = Board(size=size)
    board.add_ship(Ship(Dot(bow[0], bow[1]), length, orientation))
    board.begin()
    return board


class AIStrategyTests(unittest.TestCase):
    def test_target_mode_shoots_neighbors_after_hit(self):
        enemy = build_enemy_board((0, 0), length=2, orientation=0)
        ai = AI(Board(size=6), enemy, DummyUI(), choice_func=prefer_dot(Dot(0, 0)))

        ai.move()  # first hit at (0, 0)
        next_target = ai.ask()

        neighbors = [Dot(1, 0), Dot(0, 1)]
        self.assertIn(next_target, neighbors)

    def test_target_mode_continues_along_line_after_two_hits(self):
        enemy = build_enemy_board((0, 2), length=3, orientation=0)
        ai = AI(Board(size=6), enemy, DummyUI(), choice_func=prefer_dot(Dot(0, 2)))

        ai.move()  # hit (0, 2)
        ai.move()  # hit (1, 2) via target candidates
        next_target = ai.ask()

        self.assertEqual(next_target.x, 2)
        self.assertEqual(next_target.y, 2)


if __name__ == "__main__":
    unittest.main()
