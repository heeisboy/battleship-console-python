import time
import tkinter as tk
from tkinter import messagebox

from .core import Board, Dot, Ship, BoardException, BoardWrongShipException
from .game import GameConfig, create_game, ships_config_for_size


class TkUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Морской бой")
        self.status_var = tk.StringVar(value="")
        self.turn_status_var = tk.StringVar(value="")
        self.root_frame = tk.Frame(self.root)
        self.root_frame.pack(fill="both", expand=True)

        self.menu_frame = None
        self.placement_frame = None
        self.pass_turn_frame = None
        self.game_frame = None
        self.end_frame = None
        self._current_screen = None

        self.mode = "pve"
        self.size = 6
        self.ships_config = ships_config_for_size(self.size)

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
        self._after_id = None
        self._ai_after_id = None
        self._default_btn_bg = None

        self.p1_board = None
        self.p2_board = None
        self.game = None
        self.game_over = False
        self.locked = False
        self.input_locked = False
        self.game_buttons = {}
        self.turn_label = None
        self.ai_status_label = None
        self.log_text = None
        self.log_scroll = None
        self.log_entries = []
        self.log_controls_frame = None
        self.log_stats_label = None
        self.stats_frame = None
        self.stats_labels = {}
        self.turn_counter = 0
        self._series_actor = None
        self._series_count = 0
        self._stats = {}
        self._actors = []
        self.current_player_index = 0

        self.STATUS_MISS = "MISS"
        self.STATUS_HIT = "HIT"
        self.STATUS_KILL = "KILL"

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

    def _cancel_after_jobs(self):
        for attr in ("_after_id", "_refresh_job", "_ai_after_id"):
            job_id = getattr(self, attr)
            if job_id is None:
                continue
            try:
                self.root.after_cancel(job_id)
            except tk.TclError:
                pass
            setattr(self, attr, None)

    def _destroy_frames(self):
        for attr in ("menu_frame", "placement_frame", "pass_turn_frame", "game_frame", "end_frame"):
            frame = getattr(self, attr)
            if frame is None:
                continue
            try:
                frame.destroy()
            except tk.TclError:
                pass
            setattr(self, attr, None)

    def clear_screen(self):
        self._placement_alive = False
        self._remove_traces()
        self._destroy_frames()

    def _show_screen(self, name):
        self.clear_screen()
        self._current_screen = name

    def reset_app_state(self, mode="keep_settings"):
        self._cancel_after_jobs()
        self._remove_traces()
        self._placement_alive = False

        self.placement_board = None
        self.placement_player_index = 0
        self.placement_pool = {}
        self.selected_length.set(0)
        self.orientation_var.set("h")
        self.start_cell = None
        self.preview_dots = []
        self.preview_valid = False
        self.valid_start_cells = set()
        self.pool_labels = {}
        self.length_menu = None
        self.placement_buttons = {}
        self.confirm_button = None
        self._default_btn_bg = None

        self.p1_board = None
        self.p2_board = None
        self.game = None
        self.game_over = False
        self.locked = False
        self.input_locked = False
        self.game_buttons = {}
        self.turn_label = None
        self.ai_status_label = None
        self.log_text = None
        self.log_scroll = None
        self.log_entries = []
        self.log_controls_frame = None
        self.log_stats_label = None
        self.stats_frame = None
        self.stats_labels = {}
        self.turn_counter = 0
        self._series_actor = None
        self._series_count = 0
        self._stats = {}
        self._actors = []
        self.current_player_index = 0

        self.STATUS_MISS = "MISS"
        self.STATUS_HIT = "HIT"
        self.STATUS_KILL = "KILL"

        if mode == "to_menu":
            self.mode = "pve"
            self.size = 6
            self.ships_config = ships_config_for_size(self.size)

        self.status_var.set("")
        self.turn_status_var.set("")
        self._clear_log()
        self.turn_counter = 0
        self._reset_series()
        self._stats = {}
        self._actors = []
        self._destroy_frames()

    def say(self, message):
        self.status_var.set(message)

    def prompt(self, message):
        return ""

    def run(self):
        self.show_menu()
        self.root.mainloop()

    def show_menu(self):
        self._show_screen("menu")
        self.status_var.set("")

        self.menu_frame = tk.Frame(self.root_frame, padx=10, pady=10)
        self.menu_frame.pack()

        tk.Label(self.menu_frame, text="Выберите размер поля:").pack(anchor="w")
        size_var = tk.IntVar(value=self.size)
        for label in ["6", "8", "10"]:
            value = int(label)
            tk.Radiobutton(
                self.menu_frame,
                text=f"{label}x{label}",
                value=value,
                variable=size_var,
            ).pack(anchor="w")

        tk.Label(self.menu_frame, text="Выберите режим:").pack(anchor="w", pady=(10, 0))
        mode_var = tk.StringVar(value=self.mode)
        tk.Radiobutton(self.menu_frame, text="Игрок vs AI", value="pve", variable=mode_var).pack(anchor="w")
        tk.Radiobutton(self.menu_frame, text="Игрок vs Игрок", value="pvp", variable=mode_var).pack(anchor="w")

        def on_start():
            self.size = size_var.get()
            self.ships_config = ships_config_for_size(self.size)
            self.mode = mode_var.get()
            self.start_placement(player_index=0)

        tk.Button(self.menu_frame, text="Начать", command=on_start).pack(pady=10)
        tk.Label(self.menu_frame, textvariable=self.status_var, anchor="w").pack(fill="x")

    def start_placement(self, player_index):
        self._show_screen("placement")
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

        self.placement_frame = tk.Frame(self.root_frame, padx=10, pady=10)
        self.placement_frame.pack()

        left = tk.Frame(self.placement_frame)
        right = tk.Frame(self.placement_frame)
        left.grid(row=0, column=0, padx=10)
        right.grid(row=0, column=1, padx=10, sticky="n")

        name = "Игрок 1" if player_index == 0 else "Игрок 2"
        tk.Label(left, text=f"Расстановка: {name}").pack(anchor="w")

        def cell_factory(parent, row_index, col_index):
            btn = tk.Button(
                parent,
                width=2,
                height=1,
                command=lambda ix=row_index, iy=col_index: self.on_place_click(ix, iy),
            )
            if self._default_btn_bg is None:
                self._default_btn_bg = btn.cget("bg")
            return btn

        grid_frame, self.placement_buttons = self.create_grid_with_headers(left, self.size, cell_factory)
        grid_frame.pack()

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

        legend_items = [
            ("O", "Вода", {}),
            ("■", "Корабль", {}),
            (".", "Промах", {}),
            ("X", "Попадание", {}),
            ("O", "Туман (поле соперника)", {}),
            ("O", "Preview OK", {"bg": "lightgreen"}),
            ("O", "Preview BAD", {"bg": "tomato"}),
            ("O", "Допустимый старт", {"bg": "lightyellow"}),
        ]
        self._add_legend(right, legend_items).pack(anchor="w", pady=(10, 0), fill="x")

        tk.Label(self.placement_frame, textvariable=self.status_var, anchor="w").grid(
            row=1, column=0, columnspan=2, sticky="we"
        )

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

    def _col_labels(self, size):
        return [chr(ord("A") + idx) for idx in range(size)]

    def _row_labels(self, size):
        return [str(idx + 1) for idx in range(size)]

    def create_grid_with_headers(self, parent, size, cell_factory):
        grid_frame = tk.Frame(parent)
        buttons = {}
        col_labels = self._col_labels(size)
        row_labels = self._row_labels(size)

        row_width = max(2, len(str(size)))
        corner = tk.Label(grid_frame, text="", width=row_width)
        corner.grid(row=0, column=0)

        for col_index, label in enumerate(col_labels):
            tk.Label(grid_frame, text=label, width=2).grid(row=0, column=col_index + 1)

        for row_index, label in enumerate(row_labels):
            tk.Label(grid_frame, text=label, width=row_width).grid(row=row_index + 1, column=0)
            for col_index in range(size):
                btn = cell_factory(grid_frame, row_index, col_index)
                btn.grid(row=row_index + 1, column=col_index + 1)
                buttons[(row_index, col_index)] = btn

        return grid_frame, buttons

    def _add_legend(self, parent, items, title="Легенда"):
        frame = tk.LabelFrame(parent, text=title, padx=6, pady=6)
        for symbol, text, style in items:
            row = tk.Frame(frame)
            sample = tk.Label(
                row,
                text=symbol,
                width=2,
                height=1,
                relief="ridge",
                bg=style.get("bg"),
                fg=style.get("fg"),
            )
            sample.pack(side="left")
            tk.Label(row, text=text).pack(side="left", padx=(6, 0))
            row.pack(anchor="w")
        return frame

    def _fmt_coord(self, dot):
        cols = self._col_labels(self.size)
        if 0 <= dot.x < len(cols):
            col = cols[dot.x]
        else:
            col = str(dot.x + 1)
        return f"{col}{dot.y + 1}"

    def _log(self, msg):
        self.log_entries.append((msg, None))
        if self.log_text is None or not self.log_text.winfo_exists():
            return
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _log_with_tag(self, msg, tag=None):
        self.log_entries.append((msg, tag))
        if self.log_text is None or not self.log_text.winfo_exists():
            return
        self.log_text.config(state="normal")
        if tag:
            self.log_text.insert("end", msg + "\n", tag)
        else:
            self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _render_log(self):
        if self.log_text is None or not self.log_text.winfo_exists():
            return
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        for line, tag in self.log_entries:
            if tag:
                self.log_text.insert("end", line + "\n", tag)
            else:
                self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _clear_log(self):
        self.log_entries = []
        if self.log_text is None or not self.log_text.winfo_exists():
            return
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def _copy_log(self):
        if self.log_text is None or not self.log_text.winfo_exists():
            return
        text = self.log_text.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def _now_time(self):
        return time.strftime("%H:%M:%S")

    def _normalize_shot(self, message, repeat):
        lower = message.lower()
        if "убил" in lower or "потоп" in lower or "потопил" in lower or "уничтожен" in lower:
            status = self.STATUS_KILL
            short = "уничтожен"
        elif "попал" in lower or "ранен" in lower:
            status = self.STATUS_HIT
            short = "попадание"
        elif "мимо" in lower:
            status = self.STATUS_MISS
            short = "мимо"
        else:
            status = self.STATUS_MISS
            short = message.strip()[:40] if message else "мимо"
        if repeat:
            short += " (повтор)"
        return status, short

    def _format_stats_line(self):
        parts = []
        for actor in self._actors:
            stats = self._stats.get(actor, {"shots": 0, "hits": 0})
            shots = stats["shots"]
            hits = stats["hits"]
            accuracy = int(round((hits / shots) * 100)) if shots else 0
            parts.append(f"{actor}: {shots} выстр., {hits} попад., {accuracy}%")
        return " | ".join(parts)

    def _update_stats_label(self):
        if self.log_stats_label is None:
            return
        self.log_stats_label.config(text=self._format_stats_line())

    def _actor_boards(self):
        if not self.game:
            return {}
        if self.mode == "pvp":
            return {
                "Игрок 1": self.game.p1.board,
                "Игрок 2": self.game.p2.board,
            }
        return {
            "Игрок": self.game.us.board,
            "Компьютер": self.game.ai.board,
        }

    def _format_actor_stats(self, actor):
        stats = self._stats.get(actor, {"shots": 0, "hits": 0})
        shots = stats["shots"]
        hits = stats["hits"]
        accuracy = int(round((hits / shots) * 100)) if shots else 0
        win_count = len(self.ships_config)
        board = self._actor_boards().get(actor)
        sunk = board.count if board is not None else 0
        remaining = max(win_count - sunk, 0)
        return (
            f"{actor}: {shots} выстр., {hits} попад., {accuracy}% | "
            f"Уничтожено {sunk}/{win_count}, Осталось {remaining}"
        )

    def _refresh_stats(self):
        if not self.stats_labels:
            return
        for actor, label in self.stats_labels.items():
            label.config(text=self._format_actor_stats(actor))

    def _reset_series(self):
        self._series_actor = None
        self._series_count = 0

    def _log_event(self, kind, actor=None, dot=None, message=None, repeat=False):
        if kind == "start":
            line = f"=== Старт игры: режим {actor}, поле {self.size}x{self.size} ==="
            self._log_with_tag(line, "header")
            return
        if kind == "turn":
            self._reset_series()
            self._log_with_tag(f"— Ход: {actor} —", "header")
            return
        if kind == "win":
            self._log_with_tag(f"=== Победа: {actor} ===", "header")
            self._log_with_tag(f"Итог: {self._format_stats_line()}", "header")
            return
        if kind != "shot":
            self._log_with_tag(message or "", None)
            return

        if actor != self._series_actor:
            self._reset_series()
        if repeat:
            self._series_actor = actor
            self._series_count += 1
        else:
            self._reset_series()

        self.turn_counter += 1
        coord = self._fmt_coord(dot) if dot else "?"
        status, result_text = self._normalize_shot(message or "", repeat)
        tag = status.lower()
        line = f"[{self._now_time()}] #{self.turn_counter} [{status}] {actor}: {coord} — {result_text}"
        self._log_with_tag(line, tag)

        if actor not in self._stats:
            self._stats[actor] = {"shots": 0, "hits": 0}
        self._stats[actor]["shots"] += 1
        if tag in ("hit", "kill"):
            self._stats[actor]["hits"] += 1
        self._update_stats_label()
        self._refresh_stats()

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
        self._show_screen("pass_turn")
        self.status_var.set("")
        self.pass_turn_frame = tk.Frame(self.root_frame, padx=10, pady=10)
        self.pass_turn_frame.pack()

        tk.Label(self.pass_turn_frame, text=f"Передайте ход {next_player_name} и нажмите Продолжить").pack(pady=10)
        tk.Button(self.pass_turn_frame, text="Продолжить", command=on_continue).pack()

    def _lock_input(self, reason=None):
        self.input_locked = True
        if reason == "ai_turn":
            self.turn_status_var.set("Ход компьютера...")
        elif reason:
            self.turn_status_var.set(reason)
        self.refresh_game()

    def _unlock_input(self):
        self.input_locked = False
        if self.mode == "pve":
            self.turn_status_var.set("Ваш ход")
            if not self.game_over:
                self._log_event("turn", actor="Игрок")
        self.refresh_game()

    def _cancel_ai_job(self):
        if self._ai_after_id is None:
            return
        try:
            self.root.after_cancel(self._ai_after_id)
        except tk.TclError:
            pass
        self._ai_after_id = None

    def _schedule_ai_turn(self, delay_ms, status_message=None):
        self._cancel_ai_job()
        if status_message:
            self.turn_status_var.set(status_message)
        self._ai_after_id = self.root.after(delay_ms, self._do_ai_turn)

    def _start_new_game(self):
        self.reset_app_state(mode="keep_settings")
        self.start_placement(player_index=0)

    def _back_to_menu(self):
        self.reset_app_state(mode="to_menu")
        self.show_menu()

    def start_game(self):
        config = GameConfig(size=self.size, ships_config=self.ships_config, mode=self.mode)
        if self.mode == "pvp":
            self.game = create_game(
                config,
                ui=self,
                p1_board=self.p1_board,
                p2_board=self.p2_board,
            )
        else:
            self.game = create_game(
                config,
                ui=self,
                p1_board=self.p1_board,
                ai_board=None,
                human_name="Игрок",
            )
        self.game_over = False
        self.locked = False
        self.current_player_index = 0
        self.show_game_screen()

    def show_game_screen(self, reset_log=True):
        self._show_screen("game")
        self.status_var.set("")
        self.game_buttons = {}

        self.game_frame = tk.Frame(self.root_frame, padx=10, pady=10)
        self.game_frame.pack()

        controls = tk.Frame(self.game_frame)
        controls.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        tk.Button(controls, text="Новая игра", command=self._start_new_game).pack(side="left", padx=(0, 10))
        tk.Button(controls, text="В меню", command=self._back_to_menu).pack(side="left")

        left = tk.Frame(self.game_frame)
        right = tk.Frame(self.game_frame)
        left.grid(row=1, column=0, padx=10)
        right.grid(row=1, column=1, padx=10)

        right_panel = tk.Frame(self.game_frame)
        right_panel.grid(row=1, column=2, padx=10, sticky="ns")

        self.stats_frame = tk.LabelFrame(right_panel, text="Статистика", padx=6, pady=6)
        self.stats_frame.pack(fill="x", pady=(0, 10))
        self.stats_labels = {}

        log_frame = tk.LabelFrame(right_panel, text="Журнал", padx=6, pady=6)
        log_frame.pack(fill="both", expand=True)
        self.log_controls_frame = tk.Frame(log_frame)
        self.log_controls_frame.grid(row=0, column=0, columnspan=2, sticky="we", pady=(0, 6))
        tk.Button(self.log_controls_frame, text="Очистить", command=self._clear_log).pack(side="left")
        tk.Button(self.log_controls_frame, text="Копировать", command=self._copy_log).pack(side="left", padx=(6, 0))

        self.log_text = tk.Text(log_frame, width=36, height=18, state="disabled")
        self.log_scroll = tk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=self.log_scroll.set)
        self.log_text.grid(row=1, column=0, sticky="nsew")
        self.log_scroll.grid(row=1, column=1, sticky="ns")
        self.log_stats_label = tk.Label(log_frame, text="", anchor="w", justify="left")
        self.log_stats_label.grid(row=2, column=0, columnspan=2, sticky="we", pady=(6, 0))
        log_frame.rowconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_text.tag_configure("header", font=("TkDefaultFont", 9, "bold"))
        self.log_text.tag_configure("hit", font=("TkDefaultFont", 9, "bold"))
        self.log_text.tag_configure("kill", font=("TkDefaultFont", 9, "bold"))
        self.log_text.tag_configure("miss", font=("TkDefaultFont", 9))

        self.turn_label = tk.Label(self.game_frame, text="")
        self.turn_label.grid(row=2, column=0, columnspan=2, sticky="w")
        self.ai_status_label = tk.Label(self.game_frame, textvariable=self.turn_status_var, anchor="w")
        self.ai_status_label.grid(row=3, column=0, columnspan=2, sticky="w")
        tk.Label(self.game_frame, textvariable=self.status_var, anchor="w").grid(
            row=4, column=0, columnspan=2, sticky="we"
        )

        def left_cell_factory(parent, row_index, col_index):
            return tk.Button(parent, width=2, height=1)

        def right_cell_factory(parent, row_index, col_index):
            return tk.Button(
                parent,
                width=2,
                height=1,
                command=lambda ix=row_index, iy=col_index: self.on_game_click(ix, iy),
            )

        left_grid, left_buttons = self.create_grid_with_headers(left, self.size, left_cell_factory)
        left_grid.pack()
        right_grid, right_buttons = self.create_grid_with_headers(right, self.size, right_cell_factory)
        right_grid.pack()
        for (row_index, col_index), btn in left_buttons.items():
            self.game_buttons[("left", row_index, col_index)] = btn
        for (row_index, col_index), btn in right_buttons.items():
            self.game_buttons[("right", row_index, col_index)] = btn

        legend_items = [
            ("O", "Вода", {}),
            (".", "Промах", {}),
            ("X", "Попадание", {}),
            ("■", "Корабль (своё поле)", {}),
            ("O", "Туман (поле соперника)", {}),
        ]
        self._add_legend(self.game_frame, legend_items).grid(row=5, column=0, columnspan=3, sticky="we", pady=(10, 0))

        if self.mode == "pve":
            self.turn_status_var.set("Ваш ход")
        else:
            self.turn_status_var.set("")
        if reset_log:
            self.turn_counter = 0
            self._reset_series()
            self._stats = {}
            self._actors = ["Игрок 1", "Игрок 2"] if self.mode == "pvp" else ["Игрок", "Компьютер"]
            self._clear_log()
            mode_label = "PvP" if self.mode == "pvp" else "PvE"
            self._log_event("start", actor=mode_label)
            self._log_event("turn", actor=self._actors[0])
        else:
            self._render_log()
            self._update_stats_label()

        for actor in self._actors:
            label = tk.Label(self.stats_frame, text="", anchor="w", justify="left")
            label.pack(anchor="w")
            self.stats_labels[actor] = label
        self._refresh_stats()
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

                if Dot(x, y) in right_board.busy or self.game_over or self.locked or self.input_locked:
                    right_btn.config(state="disabled")
                else:
                    right_btn.config(state="normal")

    def on_game_click(self, x, y):
        if self.locked or self.game_over or self.input_locked:
            return

        if self.mode == "pvp":
            current = self.game.p1 if self.current_player_index == 0 else self.game.p2
            opponent = self.game.p2 if self.current_player_index == 0 else self.game.p1
            target_board = opponent.board
            shooter_name = current.name
        else:
            target_board = self.game.ai.board
            shooter_name = "Игрок"

        try:
            repeat, message = target_board.shot(Dot(x, y))
        except BoardException as e:
            self.say(str(e))
            return

        self.say(message)
        self._log_event("shot", actor=shooter_name, dot=Dot(x, y), message=message, repeat=repeat)
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
            self._log_event("turn", actor="Компьютер")
            self._lock_input("ai_turn")
            self._schedule_ai_turn(450, "Ход компьютера...")

    def _switch_player(self):
        self.current_player_index = 1 - self.current_player_index
        next_name = "Игрок 2" if self.current_player_index == 1 else "Игрок 1"
        self._log_event("turn", actor=next_name)
        self.show_game_screen(reset_log=False)

    def _do_ai_turn(self):
        self._ai_after_id = None
        board = self.game.us.board
        before_len = len(board.busy)
        repeat = self.game.ai.move()
        self.refresh_game()

        result_message = self.status_var.get()
        if len(board.busy) > before_len:
            shot_dot = board.busy[before_len]
            self._log_event("shot", actor="Компьютер", dot=shot_dot, message=result_message, repeat=repeat)

        if self.game.is_winner(self.game.us.board):
            self.finish_game("Компьютер")
            return

        if repeat:
            self._lock_input("Компьютер стреляет ещё раз...")
            self._schedule_ai_turn(300, "Компьютер стреляет ещё раз...")
        else:
            self._unlock_input()

    def show_end_screen(self, winner):
        self._show_screen("end")
        self.end_frame = tk.Frame(self.root_frame, padx=10, pady=10)
        self.end_frame.pack()

        tk.Label(self.end_frame, text=f"Победитель: {winner}").pack(pady=(0, 10))
        tk.Button(self.end_frame, text="Новая игра", command=self._start_new_game).pack(fill="x", pady=(0, 5))
        tk.Button(self.end_frame, text="В меню", command=self._back_to_menu).pack(fill="x")

    def finish_game(self, winner):
        self.game_over = True
        self.input_locked = True
        self.turn_status_var.set("")
        self.refresh_game()
        self._log_event("win", actor=winner)
        messagebox.showinfo("Игра окончена", f"{winner} выиграл!")
        self._cancel_after_jobs()
        self.show_end_screen(winner)
