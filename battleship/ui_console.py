import os


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
