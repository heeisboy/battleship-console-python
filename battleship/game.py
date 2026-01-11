from random import randint

from .core import Board, Dot, Ship, BoardWrongShipException
from .players import AI, HumanPlayer, User


class Game:
    def __init__(self, size=6, ships_config=None, ui=None, mode="pve"):
        self.size = size
        if ui is None:
            from .ui_console import ConsoleUI
            ui = ConsoleUI()
        self.ui = ui
        self.ships_config = ships_config or [3, 2, 2, 1, 1, 1, 1]
        self.win_count = len(self.ships_config)
        self.mode = mode

        if self.mode == "pvp":
            p1_board = self.random_board()
            p2_board = self.random_board()
            self.p1 = HumanPlayer(p1_board, p2_board, self.ui, "Игрок 1")
            self.p2 = HumanPlayer(p2_board, p1_board, self.ui, "Игрок 2")
            self.ai = None
            self.us = None
        else:
            pl = self.random_board()
            co = self.random_board()
            co.hid = True
            self.ai = AI(co, pl, self.ui)
            self.us = User(pl, co, self.ui)

    @classmethod
    def from_boards(
        cls,
        size=6,
        ships_config=None,
        ui=None,
        mode="pve",
        p1_board=None,
        p2_board=None,
        ai_board=None,
        human_name="Игрок",
    ):
        game = cls.__new__(cls)
        game.size = size
        if ui is None:
            from .ui_console import ConsoleUI
            ui = ConsoleUI()
        game.ui = ui
        game.ships_config = ships_config or [3, 2, 2, 1, 1, 1, 1]
        game.win_count = len(game.ships_config)
        game.mode = mode

        if game.mode == "pvp":
            if p1_board is None or p2_board is None:
                raise ValueError("pvp requires p1_board and p2_board")
            game.p1 = HumanPlayer(p1_board, p2_board, game.ui, "Игрок 1")
            game.p2 = HumanPlayer(p2_board, p1_board, game.ui, "Игрок 2")
            game.ai = None
            game.us = None
        else:
            if p1_board is None:
                p1_board = game.random_board()
            if ai_board is None:
                ai_board = game.random_board()
            ai_board.hid = True
            game.ai = AI(ai_board, p1_board, game.ui)
            game.us = HumanPlayer(p1_board, ai_board, game.ui, human_name)
        return game

    def random_board(self):
        board = None
        while board is None:
            board = self.random_place()
        return board

    def random_place(self):
        board = Board(size=self.size)
        attempts = 0
        for l in self.ships_config:
            while True:
                attempts += 1
                if attempts > 2000:
                    return None
                ship = Ship(Dot(randint(0, self.size), randint(0, self.size)), l, randint(0, 1))
                try:
                    board.add_ship(ship)
                    break
                except BoardWrongShipException:
                    pass
        board.begin()
        return board

    def greet(self):
        self.ui.greet()

    def is_winner(self, board):
        return board.count == self.win_count

    def _show_pvp_boards(self, current_player, opponent):
        # Hide opponent ships only for rendering.
        prev_hid = opponent.board.hid
        opponent.board.hid = True
        try:
            self.ui.show_pvp_boards(
                current_player.board,
                opponent.board,
                current_player.name,
                opponent.name,
            )
        finally:
            opponent.board.hid = prev_hid

    def loop(self):
        num = 0
        while True:
            if self.mode == "pvp":
                current = self.p1 if num % 2 == 0 else self.p2
                opponent = self.p2 if num % 2 == 0 else self.p1
                self._show_pvp_boards(current, opponent)
                self.ui.show_turn_header(current.name)
                repeat = current.move()

                if self.is_winner(opponent.board):
                    self.ui.show_winner(current.name)
                    break

                if repeat:
                    num -= 1
                else:
                    self.ui.pause_pass_turn(opponent.name)
            else:
                self.ui.show_boards(self.us.board, self.ai.board)
                if num % 2 == 0:
                    self.ui.announce_turn(user_turn=True)
                    repeat = self.us.move()
                else:
                    self.ui.announce_turn(user_turn=False)
                    repeat = self.ai.move()
                if repeat:
                    num -= 1

                if self.is_winner(self.ai.board):
                    self.ui.show_winner("Пользователь")
                    break

                if self.is_winner(self.us.board):
                    self.ui.show_winner("Компьютер")
                    break
            num += 1

    def start(self):
        self.greet()
        self.loop()
