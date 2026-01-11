import tkinter as tk
from tkinter import messagebox

from .core import Board, Dot, Ship, BoardException, BoardWrongShipException
from .game import Game


class TkUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Морской бой")
        self.status_var = tk.StringVar(value="")
        self.frame = None

        self.mode = "pve"
        self.size = 6
        self.ships_config = [3, 2, 2, 1, 1, 1, 1]

        self.placement_board = None
        self.placement_player_index = 0
        self.placement_pool = {}
        self.selected_length = tk.IntVar(value=0)
        self.orientation_var = tk.StringVar(value="h")
        self.start_cell = None
        self.preview_dots = []
        self.preview_valid = False
        self.valid_start_cells = set()
        self.pool_labels = {}
        self.length_menu = None
        self.placement_buttons = {}
        self.confirm_button = None
        self._placement_alive = False
        self._orientation_trace = None
        self._length_trace = None
        self._refresh_job = None
        self._default_btn_bg = None

        self.p1_board = None
        self.p2_board = None
        self.game = None
        self.game_over = False
        self.locked = False
        self.game_buttons = {}
        self.turn_label = None
        self.current_player_index = 0

        self._register_traces()

    def _register_traces(self):
        if self._orientation_trace is None:
            self._orientation_trace = self.orientation_var.trace_add("write", lambda *_: self._schedule_refresh())
        if self._length_trace is None:
            self._length_trace = self.selected_length.trace_add("write", lambda *_: self._schedule_refresh())

    def _remove_traces(self):
        if self._orientation_trace is not None:
            self.orientation_var.trace_remove("write", self._orientation_trace)
            self._orientation_trace = None
        if self._length_trace is not None:
            self.selected_length.trace_remove("write", self._length_trace)
            self._length_trace = None

    def _schedule_refresh(self):
        if not self._placement_alive:
            return
        if self._refresh_job is not None:
            try:
                self.root.after_cancel(self._refresh_job)
            except tk.TclError:
                pass
        self._refresh_job = self.root.after(0, self._refresh_preview)

    def clear_screen(self):
        self._placement_alive = False
        self._remove_traces()
        if self.frame is not None:
            self.frame.destroy()
            self.frame = None

    def say(self, message):
        self.status_var.set(message)

    def prompt(self, message):
        return ""

    def run(self):
        self.show_menu()
        self.root.mainloop()

    def show_menu(self):
        self.clear_screen()
        self.status_var.set("")

        self.frame = tk.Frame(self.root, padx=10, pady=10)
        self.frame.pack()

        tk.Label(self.frame, text="Выберите размер поля:").pack(anchor="w")
        size_var = tk.StringVar(value="6")
        for label in ["6", "8", "10"]:
            tk.Radiobutton(self.frame, text=f"{label}x{label}", value=label, variable=size_var).pack(anchor="w")

        tk.Label(self.frame, text="Выберите режим:").pack(anchor="w", pady=(10, 0))
        mode_var = tk.StringVar(value="pve")
        tk.Radiobutton(self.frame, text="Игрок vs AI", value="pve", variable=mode_var).pack(anchor="w")
        tk.Radiobutton(self.frame, text="Игрок vs Игрок", value="pvp", variable=mode_var).pack(anchor="w")

        def on_start():
            size = int(size_var.get())
            presets = {
                6: [3, 2, 2, 1, 1, 1, 1],
                8: [3, 2, 2, 2, 1, 1, 1, 1],
                10: [4, 3, 3, 2, 2, 2, 1, 1, 1, 1],
            }
            self.size = size
            self.ships_config = presets[size]
            self.mode = mode_var.get()
            self.start_placement(player_index=0)

        tk.Button(self.frame, text="Начать", command=on_start).pack(pady=10)
        tk.Label(self.frame, textvariable=self.status_var, anchor="w").pack(fill="x")

    def start_placement(self, player_index):
        self.clear_screen()
        self.status_var.set("")
        self.placement_player_index = player_index
        self.placement_board = Board(size=self.size)
        self.placement_pool = {}
        for length in self.ships_config:
            self.placement_pool[length] = self.placement_pool.get(length, 0) + 1

        self.selected_length.set(0)
        self.orientation_var.set("h")
        self.start_cell = None
        self.preview_dots = []
        self.preview_valid = False
        self.valid_start_cells = set()
        self.placement_buttons = {}
        self.pool_labels = {}
        self._placement_alive = True
        self._register_traces()

        self.frame = tk.Frame(self.root, padx=10, pady=10)
        self.frame.pack()

        left = tk.Frame(self.frame)
        right = tk.Frame(self.frame)
        left.grid(row=0, column=0, padx=10)
        right.grid(row=0, column=1, padx=10, sticky="n")

        name = "Игрок 1" if player_index == 0 else "Игрок 2"
        tk.Label(left, text=f"Расстановка: {name}").grid(row=0, column=0, columnspan=self.size)

        for x in range(self.size):
            for y in range(self.size):
                btn = tk.Button(left, width=2, height=1, command=lambda ix=x, iy=y: self.on_place_click(ix, iy))
                btn.grid(row=x + 1, column=y)
                if self._default_btn_bg is None:
                    self._default_btn_bg = btn.cget("bg")
                self.placement_buttons[(x, y)] = btn

        tk.Label(right, text="Пул кораблей:").pack(anchor="w")
        for length in sorted(self.placement_pool.keys(), reverse=True):
            label = tk.Label(right, text=self._pool_label_text(length))
            label.pack(anchor="w")
            self.pool_labels[length] = label

        tk.Label(right, text="Выберите длину:").pack(anchor="w", pady=(10, 0))
        self.length_menu = tk.OptionMenu(right, self.selected_length, self._available_lengths()[0])
        self.length_menu.pack(anchor="w")
        self._refresh_length_menu()

        tk.Label(right, text="Ориентация:").pack(anchor="w", pady=(10, 0))
        tk.Radiobutton(right, text="Горизонтально", value="h", variable=self.orientation_var).pack(anchor="w")
        tk.Radiobutton(right, text="Вертикально", value="v", variable=self.orientation_var).pack(anchor="w")

        self.confirm_button = tk.Button(right, text="Подтвердить", command=self.confirm_placement)
        self.confirm_button.pack(fill="x", pady=(10, 0))
        tk.Button(right, text="Отмена", command=self.cancel_preview).pack(fill="x")
        tk.Button(right, text="Сбросить поле", command=self.reset_placement).pack(fill="x", pady=(10, 0))
        tk.Button(right, text="Готово", command=self.finish_placement).pack(fill="x")

        tk.Label(self.frame, textvariable=self.status_var, anchor="w").grid(row=1, column=0, columnspan=2, sticky="we")

        self.valid_start_cells = self._compute_valid_starts()
        self._refresh_placement_board()

    def _pool_label_text(self, length):
        return f"Длина {length}: {self.placement_pool.get(length, 0)}"

    def _available_lengths(self):
        lengths = [l for l, c in self.placement_pool.items() if c > 0]
        if not lengths:
            return [0]
        return sorted(lengths, reverse=True)

    def _refresh_preview(self):
        if not self._placement_alive:
            return
        if not self.start_cell:
            self.preview_dots = []
            self.preview_valid = False
            self.valid_start_cells = self._compute_valid_starts()
            self._refresh_placement_board()
            return
        length = self.selected_length.get()
        if length <= 0:
            self.preview_dots = []
            self.preview_valid = False
            self.valid_start_cells = set()
            self._refresh_placement_board()
            return
        self.preview_dots = self._calc_dots(self.start_cell, length, self.orientation_var.get())
        self.preview_valid = self._validate_preview(self.preview_dots)
        self.valid_start_cells = self._compute_valid_starts()
        self._refresh_placement_board()

    def _refresh_length_menu(self):
        menu = self.length_menu["menu"]
        menu.delete(0, "end")
        lengths = self._available_lengths()
        for length in lengths:
            menu.add_command(label=str(length), command=lambda v=length: self.selected_length.set(v))
        if self.selected_length.get() not in lengths:
            self.selected_length.set(lengths[0])

    def _calc_dots(self, start, length, orientation):
        dots = []
        for i in range(length):
            x = start[0]
            y = start[1]
            if orientation == "h":
                y += i
            else:
                x += i
            dots.append(Dot(x, y))
        return dots

    def _ship_orientation_flag(self):
        # Ship.o uses 0 -> change x (vertical on screen), 1 -> change y (horizontal).
        return 1 if self.orientation_var.get() == "h" else 0

    def _validate_preview(self, dots):
        for d in dots:
            if self.placement_board.out(d) or d in self.placement_board.busy:
                return False
        return True

    def _compute_valid_starts(self):
        length = self.selected_length.get()
        if length <= 0:
            return set()
        orientation = self.orientation_var.get()
        starts = set()
        for x in range(self.size):
            for y in range(self.size):
                dots = self._calc_dots((x, y), length, orientation)
                if self._validate_preview(dots):
                    starts.add((x, y))
        return starts

    def _ship_cells(self):
        cells = set()
        for ship in self.placement_board.ships:
            for d in ship.dots:
                cells.add((d.x, d.y))
        return cells

    def _update_status(self):
        length = self.selected_length.get()
        if length > 0:
            count = self.placement_pool.get(length, 0)
            orient = "горизонтально" if self.orientation_var.get() == "h" else "вертикально"
            self.say(f"Корабль: {length} (осталось {count}), ориентация: {orient}. Выберите стартовую клетку.")
        else:
            self.say("Сначала выберите корабль из пула.")

    def on_place_click(self, x, y):
        length = self.selected_length.get()
        if length <= 0:
            self.say("Выберите корабль из пула.")
            return
        if self.placement_pool.get(length, 0) <= 0:
            self.say("Корабли этой длины закончились.")
            return

        self.start_cell = (x, y)
        dots = self._calc_dots(self.start_cell, length, self.orientation_var.get())
        self.preview_dots = dots
        self.preview_valid = self._validate_preview(dots)
        self.valid_start_cells = self._compute_valid_starts()
        self._refresh_placement_board()

    def _refresh_placement_board(self):
        if not self._placement_alive:
            return
        ship_cells = self._ship_cells()
        for x in range(self.size):
            for y in range(self.size):
                btn = self.placement_buttons[(x, y)]
                if btn is None or not btn.winfo_exists():
                    continue
                base_bg = self._default_btn_bg
                if (x, y) in ship_cells:
                    btn.config(text="■", bg=base_bg, relief="raised")
                else:
                    btn.config(text="O", bg=base_bg, relief="raised")

                if (x, y) in self.valid_start_cells and (x, y) not in ship_cells:
                    btn.config(bg="lightyellow")

        for d in self.preview_dots:
            if self.placement_board.out(d):
                continue
            btn = self.placement_buttons[(d.x, d.y)]
            if btn is None or not btn.winfo_exists():
                continue
            btn.config(bg="lightgreen" if self.preview_valid else "tomato")

        for length, label in self.pool_labels.items():
            label.config(text=self._pool_label_text(length))

        if self.placement_pool:
            self._refresh_length_menu()
        if self.confirm_button is not None:
            self.confirm_button.config(state="normal" if self.preview_valid else "disabled")
        self._update_status()

    def cancel_preview(self):
        self.start_cell = None
        self.preview_dots = []
        self.preview_valid = False
        self.valid_start_cells = self._compute_valid_starts()
        self._refresh_placement_board()

    def confirm_placement(self):
        length = self.selected_length.get()
        if length <= 0:
            self.say("Выберите корабль из пула.")
            return
        if not self.start_cell:
            self.say("Выберите стартовую клетку.")
            return
        if self.placement_pool.get(length, 0) <= 0:
            self.say("Корабли этой длины закончились.")
            return

        dots = self._calc_dots(self.start_cell, length, self.orientation_var.get())
        if not self._validate_preview(dots):
            messagebox.showwarning("Ошибка", "Нельзя поставить корабль в выбранное место.")
            return

        ship = Ship(Dot(self.start_cell[0], self.start_cell[1]), length, self._ship_orientation_flag())
        try:
            self.placement_board.add_ship(ship)
        except BoardWrongShipException:
            messagebox.showwarning("Ошибка", "Нельзя поставить корабль в выбранное место.")
            return

        self.placement_pool[length] -= 1
        if self.placement_pool[length] <= 0:
            del self.placement_pool[length]

        self.start_cell = None
        self.preview_dots = []
        self.preview_valid = False
        self.valid_start_cells = self._compute_valid_starts()
        self._refresh_placement_board()

    def reset_placement(self):
        self._placement_alive = False
        self.start_placement(self.placement_player_index)

    def finish_placement(self):
        if any(count > 0 for count in self.placement_pool.values()):
            self.say("Сначала расставьте все корабли.")
            return

        self.placement_board.begin()
        if self.placement_player_index == 0:
            self.p1_board = self.placement_board
        else:
            self.p2_board = self.placement_board

        if self.mode == "pvp" and self.placement_player_index == 0:
            self.show_pass_screen("Игрок 2", lambda: self.start_placement(player_index=1))
            return

        self.start_game()

    def show_pass_screen(self, next_player_name, on_continue):
        self.clear_screen()
        self.status_var.set("")
        self.frame = tk.Frame(self.root, padx=10, pady=10)
        self.frame.pack()

        tk.Label(self.frame, text=f"Передайте ход {next_player_name} и нажмите Продолжить").pack(pady=10)
        tk.Button(self.frame, text="Продолжить", command=on_continue).pack()

    def start_game(self):
        if self.mode == "pvp":
            self.game = Game.from_boards(
                size=self.size,
                ships_config=self.ships_config,
                ui=self,
                mode="pvp",
                p1_board=self.p1_board,
                p2_board=self.p2_board,
            )
        else:
            self.game = Game.from_boards(
                size=self.size,
                ships_config=self.ships_config,
                ui=self,
                mode="pve",
                p1_board=self.p1_board,
                ai_board=None,
                human_name="Игрок",
            )
        self.game_over = False
        self.locked = False
        self.current_player_index = 0
        self.show_game_screen()

    def show_game_screen(self):
        self.clear_screen()
        self.status_var.set("")
        self.game_buttons = {}

        self.frame = tk.Frame(self.root, padx=10, pady=10)
        self.frame.pack()

        left = tk.Frame(self.frame)
        right = tk.Frame(self.frame)
        left.grid(row=0, column=0, padx=10)
        right.grid(row=0, column=1, padx=10)

        self.turn_label = tk.Label(self.frame, text="")
        self.turn_label.grid(row=1, column=0, columnspan=2, sticky="w")
        tk.Label(self.frame, textvariable=self.status_var, anchor="w").grid(row=2, column=0, columnspan=2, sticky="we")

        size = self.size
        for x in range(size):
            for y in range(size):
                b_left = tk.Button(left, width=2, height=1)
                b_left.grid(row=x + 1, column=y)
                self.game_buttons[("left", x, y)] = b_left

                b_right = tk.Button(
                    right,
                    width=2,
                    height=1,
                    command=lambda ix=x, iy=y: self.on_game_click(ix, iy),
                )
                b_right.grid(row=x + 1, column=y)
                self.game_buttons[("right", x, y)] = b_right

        self.refresh_game()

    def refresh_game(self):
        if not self.game:
            return

        if self.mode == "pvp":
            current = self.game.p1 if self.current_player_index == 0 else self.game.p2
            opponent = self.game.p2 if self.current_player_index == 0 else self.game.p1
            left_board = current.board
            right_board = opponent.board
            current_name = current.name
        else:
            left_board = self.game.us.board
            right_board = self.game.ai.board
            current_name = "Игрок"

        self.turn_label.config(text=f"Ход: {current_name}")

        for x in range(self.size):
            for y in range(self.size):
                left_btn = self.game_buttons[("left", x, y)]
                left_btn.config(text=left_board.field[x][y])

                right_btn = self.game_buttons[("right", x, y)]
                cell = right_board.field[x][y]
                if cell == "■":
                    cell = "O"
                right_btn.config(text=cell)

                if Dot(x, y) in right_board.busy or self.game_over or self.locked:
                    right_btn.config(state="disabled")
                else:
                    right_btn.config(state="normal")

    def on_game_click(self, x, y):
        if self.locked or self.game_over:
            return

        if self.mode == "pvp":
            current = self.game.p1 if self.current_player_index == 0 else self.game.p2
            opponent = self.game.p2 if self.current_player_index == 0 else self.game.p1
            target_board = opponent.board
        else:
            target_board = self.game.ai.board

        try:
            repeat, message = target_board.shot(Dot(x, y))
        except BoardException as e:
            self.say(str(e))
            return

        self.say(message)
        self.refresh_game()

        if self.game.is_winner(target_board):
            winner = "Игрок"
            if self.mode == "pvp":
                winner = "Игрок 1" if self.current_player_index == 0 else "Игрок 2"
            self.finish_game(winner)
            return

        if repeat:
            return

        if self.mode == "pvp":
            next_name = "Игрок 2" if self.current_player_index == 0 else "Игрок 1"
            self.show_pass_screen(next_name, self._switch_player)
        else:
            self.locked = True
            self.root.after(400, self.ai_turn)

    def _switch_player(self):
        self.current_player_index = 1 - self.current_player_index
        self.show_game_screen()

    def ai_turn(self):
        repeat = self.game.ai.move()
        self.refresh_game()

        if self.game.is_winner(self.game.us.board):
            self.finish_game("Компьютер")
            return

        if repeat:
            self.root.after(400, self.ai_turn)
        else:
            self.locked = False
            self.refresh_game()

    def finish_game(self, winner):
        self.game_over = True
        self.refresh_game()
        messagebox.showinfo("Игра окончена", f"{winner} выиграл!")

        def restart():
            self.show_menu()

        if self.frame is not None:
            tk.Button(self.frame, text="Новая игра", command=restart).grid(row=3, column=0, columnspan=2, pady=10)
