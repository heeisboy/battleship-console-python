import random

from .core import BoardException, Dot


class Player:
    def __init__(self, board, enemy, ui):
        self.board = board
        self.enemy = enemy
        self.ui = ui

    def ask(self):
        raise NotImplementedError()

    def move(self):
        while True:
            try:
                target = self.ask()
                repeat, message = self.enemy.shot(target)
                self.ui.say(message)
                return repeat
            except BoardException as e:
                self.ui.say(str(e))


class AI(Player):
    def __init__(self, board, enemy, ui, choice_func=None):
        super().__init__(board, enemy, ui)
        self.choice_func = choice_func or random.choice
        self.mode = "hunt"
        self.hits = []
        self.candidates = []
        self.orientation = None

    def _available_dots(self):
        dots = []
        for x in range(self.enemy.size):
            for y in range(self.enemy.size):
                d = Dot(x, y)
                if d not in self.enemy.busy:
                    dots.append(d)
        return dots

    def _hunt_candidates(self):
        # Checkerboard filter speeds up search for ships of length >= 2.
        dots = [
            d for d in self._available_dots()
            if (d.x + d.y) % 2 == 0
        ]
        return dots or self._available_dots()

    def _neighbors(self, d):
        near = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        res = []
        for dx, dy in near:
            cur = Dot(d.x + dx, d.y + dy)
            if not self.enemy.out(cur) and cur not in self.enemy.busy:
                res.append(cur)
        return res

    def _update_orientation(self):
        if len(self.hits) < 2:
            return
        # "h" -> same row, "v" -> same column.
        if self.hits[0].x == self.hits[1].x:
            self.orientation = "h"
        elif self.hits[0].y == self.hits[1].y:
            self.orientation = "v"

    def _line_candidates(self):
        if not self.orientation:
            return []
        if self.orientation == "h":
            x = self.hits[0].x
            ys = [h.y for h in self.hits]
            left = Dot(x, min(ys) - 1)
            right = Dot(x, max(ys) + 1)
            line = [left, right]
        else:
            y = self.hits[0].y
            xs = [h.x for h in self.hits]
            up = Dot(min(xs) - 1, y)
            down = Dot(max(xs) + 1, y)
            line = [up, down]
        res = []
        for d in line:
            if not self.enemy.out(d) and d not in self.enemy.busy:
                res.append(d)
        return res

    def _process_shot_result(self, target, message):
        is_hit = "ранен" in message or "уничтожен" in message
        is_sink = "уничтожен" in message
        if is_hit:
            self.hits.append(target)
            if self.mode != "target":
                self.mode = "target"
            self._update_orientation()
            if self.orientation:
                self.candidates = self._line_candidates()
            else:
                self.candidates = self._neighbors(target)
        if is_sink:
            # Ship destroyed: reset to search mode.
            self.mode = "hunt"
            self.hits = []
            self.candidates = []
            self.orientation = None

    def ask(self):
        if self.mode == "target" and self.candidates:
            d = self.candidates.pop(0)
        else:
            d = self.choice_func(self._hunt_candidates())
        self.ui.say(f"Ход компьютера: {d.x+1} {d.y+1}")
        return d

    def move(self):
        while True:
            try:
                target = self.ask()
                repeat, message = self.enemy.shot(target)
                self._process_shot_result(target, message)
                self.ui.say(message)
                return repeat
            except BoardException as e:
                self.ui.say(str(e))


class User(Player):
    def ask(self):
        while True:
            cords = self.ui.prompt("Ваш ход: ").split()

            if len(cords) != 2:
                self.ui.say(" Введите 2 координаты! ")
                continue

            x, y = cords

            if not(x.isdigit()) or not(y.isdigit()):
                self.ui.say(" Введите числа! ")
                continue

            x, y = int(x), int(y)

            return Dot(x-1, y-1)


class HumanPlayer(Player):
    def __init__(self, board, enemy, ui, name, prompt_label=None):
        super().__init__(board, enemy, ui)
        self.name = name
        self.prompt_label = prompt_label or f"{name}, ваш ход: "

    def ask(self):
        while True:
            cords = self.ui.prompt(self.prompt_label).split()

            if len(cords) != 2:
                self.ui.say(" Введите 2 координаты! ")
                continue

            x, y = cords

            if not(x.isdigit()) or not(y.isdigit()):
                self.ui.say(" Введите числа! ")
                continue

            x, y = int(x), int(y)

            return Dot(x-1, y-1)
