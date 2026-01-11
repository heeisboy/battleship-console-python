from random import randint
import random
import os

class Dot:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
    
    def __repr__(self):
        return f"({self.x}, {self.y})"


class BoardException(Exception):
    pass

class BoardOutException(BoardException):
    def __str__(self):
        return "Вы пытаетесь выстрелить за доску!"

class BoardUsedException(BoardException):
    def __str__(self):
        return "Вы уже стреляли в эту клетку"

class BoardWrongShipException(BoardException):
    pass

class Ship:
    def __init__(self, bow, l, o):
        self.bow = bow
        self.l = l
        self.o = o
        self.lives = l
    
    @property
    def dots(self):
        ship_dots = []
        for i in range(self.l):
            cur_x = self.bow.x 
            cur_y = self.bow.y
            
            if self.o == 0:
                cur_x += i
            
            elif self.o == 1:
                cur_y += i
            
            ship_dots.append(Dot(cur_x, cur_y))
        
        return ship_dots
    
    def shooten(self, shot):
        return shot in self.dots

class Board:
    def __init__(self, hid = False, size = 6):
        self.size = size
        self.hid = hid
        
        self.count = 0
        
        self.field = [ ["O"]*size for _ in range(size) ]
        
        self.busy = []
        self.ships = []
    
    def add_ship(self, ship):
        
        for d in ship.dots:
            if self.out(d) or d in self.busy:
                raise BoardWrongShipException()
        for d in ship.dots:
            self.field[d.x][d.y] = "■"
            self.busy.append(d)
        
        self.ships.append(ship)
        self.contour(ship)
            
    def contour(self, ship, verb = False):
        near = [
            (-1, -1), (-1, 0) , (-1, 1),
            (0, -1), (0, 0) , (0 , 1),
            (1, -1), (1, 0) , (1, 1)
        ]
        for d in ship.dots:
            for dx, dy in near:
                cur = Dot(d.x + dx, d.y + dy)
                if not(self.out(cur)) and cur not in self.busy:
                    if verb:
                        self.field[cur.x][cur.y] = "."
                    self.busy.append(cur)
    
    def __str__(self):
        res = ""
        width = len(str(self.size))
        header_cells = [str(i + 1).rjust(width) for i in range(self.size)]
        res += " " * width + " | " + " | ".join(header_cells) + " |"
        for i, row in enumerate(self.field):
            row_num = str(i + 1).rjust(width)
            row_cells = [cell.rjust(width) for cell in row]
            res += f"\n{row_num} | " + " | ".join(row_cells) + " |"
        
        if self.hid:
            res = res.replace("■", "O")
        return res
    
    def out(self, d):
        return not((0<= d.x < self.size) and (0<= d.y < self.size))

    def shot(self, d):
        if self.out(d):
            raise BoardOutException()
        
        if d in self.busy:
            raise BoardUsedException()
        
        self.busy.append(d)
        
        for ship in self.ships:
            if d in ship.dots:
                ship.lives -= 1
                self.field[d.x][d.y] = "X"
                if ship.lives == 0:
                    self.count += 1
                    self.contour(ship, verb = True)
                    return False, "Корабль уничтожен!"
                return True, "Корабль ранен!"
        
        self.field[d.x][d.y] = "."
        return False, "Мимо!"
    
    def begin(self):
        # After placement, busy is reused to track shots during the game.
        self.busy = []

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

class Game:
    def __init__(self, size = 6, ships_config = None, ui = None, mode = "pve"):
        self.size = size
        self.ui = ui or ConsoleUI()
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
    
    def random_board(self):
        board = None
        while board is None:
            board = self.random_place()
        return board
    
    def random_place(self):
        board = Board(size = self.size)
        attempts = 0
        for l in self.ships_config:
            while True:
                attempts += 1
                if attempts > 2000:
                    return None
                ship = Ship(Dot(randint(0, self.size), randint(0, self.size)), l, randint(0,1))
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
                    self.ui.announce_turn(user_turn = True)
                    repeat = self.us.move()
                else:
                    self.ui.announce_turn(user_turn = False)
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


class ConsoleUI:
    def say(self, message):
        print(message)

    def prompt(self, message):
        return input(message)

    def greet(self):
        print("-------------------")
        print("  Приветсвуем вас  ")
        print("      в игре       ")
        print("    морской бой    ")
        print("-------------------")
        print(" формат ввода: x y ")
        print(" x - номер строки  ")
        print(" y - номер столбца ")

    def show_boards(self, user_board, ai_board):
        print("-"*20)
        print("Доска пользователя:")
        print(user_board)
        print("-"*20)
        print("Доска компьютера:")
        print(ai_board)

    def announce_turn(self, user_turn):
        print("-"*20)
        if user_turn:
            print("Ходит пользователь!")
        else:
            print("Ходит компьютер!")

    def show_winner(self, winner):
        print("-"*20)
        print(f"{winner} выиграл!")

    def clear_screen(self):
        os.system("cls" if os.name == "nt" else "clear")

    def pause_pass_turn(self, next_player_name):
        print(f"Передайте ход {next_player_name} и нажмите Enter")
        input()
        self.clear_screen()

    def show_turn_header(self, player_name):
        print(f"Ход: {player_name}")

    def show_pvp_boards(self, left_board, right_board, left_name, right_name):
        left_lines = str(left_board).splitlines()
        right_lines = str(right_board).splitlines()
        left_width = max(len(line) for line in left_lines) if left_lines else 0
        gap = "    "
        print(f"Поле {left_name}:".ljust(left_width) + gap + f"Поле {right_name}:")
        for left, right in zip(left_lines, right_lines):
            print(left.ljust(left_width) + gap + right)
    def choose_game_settings(self):
        presets = {
            "1": (6, [3, 2, 2, 1, 1, 1, 1]),
            "2": (8, [3, 2, 2, 2, 1, 1, 1, 1]),
            "3": (10, [4, 3, 3, 2, 2, 2, 1, 1, 1, 1]),
        }
        print("-------------------")
        print("Выберите размер поля:")
        print(" 1) 6x6")
        print(" 2) 8x8")
        print(" 3) 10x10")
        choice = input("Ваш выбор (по умолчанию 1): ").strip()
        size, ships_config = presets.get(choice, presets["1"])
        return size, ships_config

    def choose_game_mode(self):
        print("-------------------")
        print("Выберите режим:")
        print(" 1) Игрок vs AI")
        print(" 2) Игрок vs Игрок")
        choice = input("Ваш выбор (по умолчанию 1): ").strip()
        return "pvp" if choice == "2" else "pve"
            
            
if __name__ == "__main__":
    ui = ConsoleUI()
    mode = ui.choose_game_mode()
    size, ships_config = ui.choose_game_settings()
    g = Game(size = size, ships_config = ships_config, ui = ui, mode = mode)
    g.start()
