import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from battleship.core import (
    Dot,
    Ship,
    Board,
    BoardWrongShipException,
    BoardUsedException,
)


def build_board_with_ship(bow, length, orientation=0, size=6):
    board = Board(size=size)
    ship = Ship(Dot(bow[0], bow[1]), length, orientation)
    board.add_ship(ship)
    board.begin()
    return board, ship


class BoardLogicTests(unittest.TestCase):
    def test_hit_returns_repeat_and_message(self):
        board, ship = build_board_with_ship((0, 0), length=2, orientation=0)
        repeat, message = board.shot(Dot(0, 0))

        self.assertTrue(repeat)
        self.assertIn("ранен", message)
        self.assertEqual(ship.lives, 1)
        self.assertTrue(ship.shooten(Dot(0, 0)))

    def test_miss_returns_no_repeat_and_marks_busy(self):
        board, _ = build_board_with_ship((0, 0), length=1, orientation=0)
        repeat, message = board.shot(Dot(5, 5))

        self.assertFalse(repeat)
        self.assertIn("Мимо", message)
        self.assertIn(Dot(5, 5), board.busy)
        self.assertEqual(board.field[5][5], ".")

    def test_repeat_shot_raises(self):
        board, _ = build_board_with_ship((0, 0), length=1, orientation=0)
        board.shot(Dot(0, 0))

        with self.assertRaises(BoardUsedException):
            board.shot(Dot(0, 0))

    def test_sink_increases_count_and_contours(self):
        board, _ = build_board_with_ship((1, 1), length=1, orientation=0)
        repeat, message = board.shot(Dot(1, 1))

        self.assertFalse(repeat)
        self.assertIn("уничтожен", message)
        self.assertEqual(board.count, 1)
        self.assertIn(Dot(0, 0), board.busy)
        self.assertEqual(board.field[0][0], ".")

    def test_add_ship_rejects_out_of_bounds_and_adjacent(self):
        board = Board(size=6)
        with self.assertRaises(BoardWrongShipException):
            board.add_ship(Ship(Dot(6, 0), 1, 0))

        board.add_ship(Ship(Dot(0, 0), 2, 1))
        with self.assertRaises(BoardWrongShipException):
            board.add_ship(Ship(Dot(1, 1), 1, 0))


if __name__ == "__main__":
    unittest.main()
