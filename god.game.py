# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║                    ВОЗВЫШЕННЫЙ: ПОСЛЕДНИЙ АЛТАРЬ                  ║
║                 Консольный симулятор молодого бога                 ║
╚══════════════════════════════════════════════════════════════════════╝

Python 3.x
Используется только стандартная библиотека.

Главные классы:
    Villager - отдельный житель деревни
    Village  - состояние деревни и её ресурсы
    God      - параметры божества
    Event    - случайное событие
    Game     - игровой цикл и интерфейс

Игра рассчитана на несколько партий.
Состояние сохраняется в JSON-файл.
"""

import json
import os
import random
import textwrap
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict


# ═════════════════════════════════════════════════════════════════════
# ЦВЕТА И ОФОРМЛЕНИЕ
# ═════════════════════════════════════════════════════════════════════

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"

SAVE_FILE = "god_save.json"


def color(text: str, code: str) -> str:
    """Добавляет ANSI-цвет."""
    return f"{code}{text}{RESET}"


def clear_screen():
    """Очищает терминал."""
    os.system("cls" if os.name == "nt" else "clear")


def line(char="─", length=68):
    return char * length


def title(text: str):
    """Красивый заголовок раздела."""
    print()
    print(color("╔" + "═" * 66 + "╗", CYAN))
    print(color("║", CYAN) + color(text.center(66), BOLD) + color("║", CYAN))
    print(color("╚" + "═" * 66 + "╝", CYAN))


def box(lines: List[str], width=66):
    """Выводит текст внутри рамки."""
    print(color("┌" + "─" * width + "┐", CYAN))

    for raw in lines:
        wrapped = textwrap.wrap(str(raw), width=width - 2) or [""]
        for item in wrapped:
            print(
                color("│", CYAN)
                + " "
                + item.ljust(width - 2)
                + " "
                + color("│", CYAN)
            )

    print(color("└" + "─" * width + "┘", CYAN))


def pause():
    input(color("\n  Нажмите ENTER, чтобы продолжить...", DIM))


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def bar(value, maximum, width=20):
    """Создаёт маленькую полоску состояния."""
    if maximum <= 0:
        maximum = 1

    ratio = clamp(value / maximum, 0, 1)
    filled = int(ratio * width)

    return "█" * filled + "░" * (width - filled)


def ask_int(prompt, minimum, maximum):
    """Безопасный ввод числа."""
    while True:
        try:
            value = int(input(prompt).strip())
            if minimum <= value <= maximum:
                return value
        except (ValueError, EOFError):
            pass

        print(
            color(
                f"  Введите число от {minimum} до {maximum}.",
                YELLOW
            )
        )


# ═════════════════════════════════════════════════════════════════════
# ASCII-АРТ
# ═════════════════════════════════════════════════════════════════════

TEMPLE_ART = r"""
                 ✦
                / \
               /___\
              |     |
              |  ✧  |
          ____|     |____
         /               \
        /_________________\
             |       |
             |       |
          ___|_______|___
"""

VILLAGE_ART = r"""
             /\                    /\
            /  \      ☼           /  \
       /\  /____\                /____\
      /  \/      \      /\       | [] |
     /____\  []   \    /  \      |    |
        ||        ||   /____\    |____|
        ||________||      ||
             ||            ||
        ~~~~~~~~~~~~~~~~~~~~~~~
"""

TREE_ART = r"""
              /\
             /**\
            /****\
           /******\
          /********\
             ||||
             ||||
             ||||
"""


# ═════════════════════════════════════════════════════════════════════
# ЖИТЕЛЬ
# ═════════════════════════════════════════════════════════════════════

@dataclass
class Villager:
    """
    Один житель.

    happiness:
        0-100 — насколько человек доволен жизнью.

    faith:
        0-100 — личная вера в божество.

    health:
        0-100 — здоровье.

    age:
        Возраст в годах.

    profession:
        Работа жителя.
    """

    name: str
    age: int
    profession: str
    happiness: int
    faith: int
    health: int
    alive: bool = True
    sick: bool = False

    def daily_faith(self):
        """Определяет, сколько веры житель генерирует."""
        if not self.alive:
            return 0

        base = 1

        if self.happiness >= 70:
            base += 1

        if self.faith >= 70:
            base += 1

        if self.sick:
            base = max(0, base - 1)

        return base

    def mood(self):
        """Человеческое описание настроения."""
        if self.happiness >= 85:
            return "счастлив"
        if self.happiness >= 65:
            return "доволен"
        if self.happiness >= 45:
            return "спокоен"
        if self.happiness >= 25:
            return "недоволен"
        return "в отчаянии"

    def faith_description(self):
        """Описание личной веры."""
        if self.faith >= 90:
            return "непоколебимая"
        if self.faith >= 70:
            return "крепкая"
        if self.faith >= 50:
            return "обычная"
        if self.faith >= 25:
            return "слабая"
        return "почти исчезла"

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


# ═════════════════════════════════════════════════════════════════════
# ДЕРЕВНЯ
# ═════════════════════════════════════════════════════════════════════

@dataclass
class Village:
    """
    Центральное состояние деревни.

    Ресурсы:
        food  - пища
        wood  - дерево
        stone - камень
        gold  - редкий материал/монеты

    temple_level:
        Уровень храма.

    morale:
        Общий моральный дух деревни.
    """

    name: str = "Лунная Долина"

    food: int = 80
    wood: int = 60
    stone: int = 45
    gold: int = 20

    temple_level: int = 1
    morale: int = 65

    year: int = 1
    season: int = 1

    villagers: List[Villager] = field(default_factory=list)

    total_blessings: int = 0
    total_sacrifices: int = 0
    disasters_survived: int = 0

    def population(self):
        return sum(1 for v in self.villagers if v.alive)

    def sick_count(self):
        return sum(1 for v in self.villagers if v.alive and v.sick)

    def average_faith(self):
        alive = [v for v in self.villagers if v.alive]

        if not alive:
            return 0

        return sum(v.faith for v in alive) // len(alive)

    def average_happiness(self):
        alive = [v for v in self.villagers if v.alive]

        if not alive:
            return 0

        return sum(v.happiness for v in alive) // len(alive)

    def production(self):
        """
        Рассчитывает производство за ход.

        Работа каждого человека зависит от профессии.
        """
        food = 0
        wood = 0
        stone = 0
        gold = 0

        for villager in self.villagers:
            if not villager.alive:
                continue

            efficiency = 1.0

            if villager.happiness < 35:
                efficiency *= 0.7

            if villager.health < 40:
                efficiency *= 0.6

            if villager.sick:
                efficiency *= 0.5

            if villager.profession == "Фермер":
                food += max(1, int(4 * efficiency))

            elif villager.profession == "Дровосек":
                wood += max(1, int(3 * efficiency))

            elif villager.profession == "Каменщик":
                stone += max(1, int(3 * efficiency))

            elif villager.profession == "Торговец":
                gold += max(1, int(2 * efficiency))

            elif villager.profession == "Жрец":
                # Жрец не создаёт материальные ресурсы,
                # зато немного усиливает храмовую жизнь.
                pass

        return food, wood, stone, gold

    def consume_food(self):
        """
        Потребление еды населением.

        Чем больше людей — тем больше еды необходимо.
        """
        cost = self.population() * 2

        if self.food >= cost:
            self.food -= cost
            return True, cost

        missing = cost - self.food
        self.food = 0

        # Недоедание влияет на людей.
        for villager in self.villagers:
            if villager.alive:
                villager.health = clamp(villager.health - 8, 0, 100)
                villager.happiness = clamp(
                    villager.happiness - 10,
                    0,
                    100
                )

        return False, missing

    def seasonal_change(self):
        """
        Переход между сезонами.

        Каждые 4 хода начинается новый год.
        """
        self.season += 1

        if self.season > 4:
            self.season = 1
            self.year += 1

    def season_name(self):
        return {
            1: "Весна",
            2: "Лето",
            3: "Осень",
            4: "Зима"
        }.get(self.season, "Неизвестно")

    def add_villager(self, villager):
        self.villagers.append(villager)

    def remove_departed(self):
        """Физически удаляет ушедших жителей."""
        self.villagers = [
            v for v in self.villagers
            if v.alive
        ]

    def temple_upgrade_cost(self):
        """
        Цена следующего уровня храма.
        """
        level = self.temple_level

        return {
            "wood": 35 + level * 25,
            "stone": 25 + level * 20,
            "gold": 10 + level * 10
        }

    def can_upgrade_temple(self):
        cost = self.temple_upgrade_cost()

        return (
            self.wood >= cost["wood"]
            and self.stone >= cost["stone"]
            and self.gold >= cost["gold"]
        )

    def upgrade_temple(self):
        """
        Улучшение храма.

        Максимальный уровень — 7.
        """
        if self.temple_level >= 7:
            return False, "Храм уже достиг своего предела."

        cost = self.temple_upgrade_cost()

        if not self.can_upgrade_temple():
            return False, "Недостаточно ресурсов."

        self.wood -= cost["wood"]
        self.stone -= cost["stone"]
        self.gold -= cost["gold"]

        self.temple_level += 1

        # Улучшение храма слегка поднимает настроение.
        for villager in self.villagers:
            if villager.alive:
                villager.happiness = clamp(
                    villager.happiness + 3,
                    0,
                    100
                )

        return True, (
            f"Храм возвышается над деревней. "
            f"Теперь его уровень — {self.temple_level}."
        )

    def to_dict(self):
        data = asdict(self)
        data["villagers"] = [
            v.to_dict()
            for v in self.villagers
        ]
        return data

    @classmethod
    def from_dict(cls, data):
        villagers = [
            Villager.from_dict(v)
            for v in data.pop("villagers", [])
        ]

        village = cls(**data)
        village.villagers = villagers
        return village


# ═════════════════════════════════════════════════════════════════════
# БОЖЕСТВО
# ═════════════════════════════════════════════════════════════════════

@dataclass
class God:
    """
    Параметры самого игрока.

    faith:
        Основная валюта чудес.

    favor:
        Благосклонность жителей. В отличие от веры,
        это более долгосрочный показатель.

    glory:
        Слава божества.

    mercy / wrath:
        Следят за стилем игры.
    """

    name: str = "Безымянный"
    faith: int = 45
    favor: int = 50
    glory: int = 0

    mercy: int = 0
    wrath: int = 0

    miracles_used: int = 0
    answered_prayers: int = 0
    ignored_prayers: int = 0

    secret_points: int = 0

    def gain_faith(self, amount):
        self.faith = clamp(self.faith + amount, 0, 999)

    def spend_faith(self, amount):
        if self.faith < amount:
            return False

        self.faith -= amount
        return True

    def miracle_power(self):
        """
        Сила чудес зависит от уровня храма и общей веры.
        """
        return 1.0

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


# ═════════════════════════════════════════════════════════════════════
# СОБЫТИЯ
# ═════════════════════════════════════════════════════════════════════

class Event:
    """
    Случайное событие.

    Событие имеет название, описание и функцию исполнения.
    """

    def __init__(self, name, description, event_id):
        self.name = name
        self.description = description
        self.event_id = event_id

    def trigger(self, game):
        """
        Выполняет событие.

        Каждое событие намеренно имеет несколько последствий.
        """
        village = game.village
        god = game.god

        print()
        print(color("╔" + "═" * 66 + "╗", MAGENTA))
        print(
            color("║", MAGENTA)
            + color(
                f"  ⚠ Событие: {self.name}".ljust(66),
                BOLD
            )
            + color("║", MAGENTA)
        )
        print(color("╚" + "═" * 66 + "╝", MAGENTA))

        box([self.description])

        # ─────────────────────────────────────────────────────────────
        # НЕУРОЖАЙ
        # ─────────────────────────────────────────────────────────────
        if self.event_id == "drought":
            loss = min(village.food, 25 + village.population())

            village.food -= loss
            village.morale = clamp(village.morale - 8, 0, 100)

            for v in village.villagers:
                if v.alive:
                    v.happiness = clamp(v.happiness - 5, 0, 100)

            print(
                color(
                    f"\n  Поля дали меньше обычного. Потеряно еды: {loss}.",
                    RED
                )
            )

        # ─────────────────────────────────────────────────────────────
        # ВОЛКИ
        # ─────────────────────────────────────────────────────────────
        elif self.event_id == "wolves":
            loss = min(village.food, random.randint(5, 15))
            village.food -= loss
            village.morale = clamp(village.morale - 5, 0, 100)

            print(
                color(
                    f"\n  Волки добрались до запасов. "
                    f"Уничтожено еды: {loss}.",
                    RED
                )
            )

        # ─────────────────────────────────────────────────────────────
        # БОЛЕЗНЬ
        # ─────────────────────────────────────────────────────────────
        elif self.event_id == "plague":
            candidates = [
                v for v in village.villagers
                if v.alive
            ]

            count = min(
                len(candidates),
                random.randint(1, max(1, len(candidates) // 3))
            )

            for v in random.sample(candidates, count):
                v.sick = True
                v.health = clamp(v.health - 15, 0, 100)
                v.happiness = clamp(v.happiness - 8, 0, 100)

            village.morale = clamp(village.morale - 7, 0, 100)

            print(
                color(
                    f"\n  Болезнь коснулась {count} жителей.",
                    RED
                )
            )

        # ─────────────────────────────────────────────────────────────
        # СТРАННИК
        # ─────────────────────────────────────────────────────────────
        elif self.event_id == "traveler":
            print(
                color(
                    "\n  Странник просит ночлега у храма.",
                    YELLOW
                )
            )

            choice = ask_int(
                "\n  [1] Приютить его\n"
                "  [2] Отказать\n"
                "  > ",
                1,
                2
            )

            if choice == 1:
                village.food = max(0, village.food - 8)
                village.gold += 15
                god.gain_faith(8)
                god.mercy += 1

                print(
                    color(
                        "  Утром странник оставил мешочек монет.",
                        GREEN
                    )
                )

            else:
                god.wrath += 1
                village.morale = clamp(
                    village.morale - 2,
                    0,
                    100
                )

                print(
                    color(
                        "  Странник ушёл до рассвета.",
                        DIM
                    )
                )

        # ─────────────────────────────────────────────────────────────
        # РОЖДЕНИЕ
        # ─────────────────────────────────────────────────────────────
        elif self.event_id == "birth":
            names = game.available_names()

            if names:
                name = random.choice(names)

                baby = Villager(
                    name=name,
                    age=0,
                    profession="Ученик",
                    happiness=75,
                    faith=70,
                    health=95
                )

                village.add_villager(baby)
                village.morale = clamp(
                    village.morale + 5,
                    0,
                    100
                )

                god.gain_faith(6)

                print(
                    color(
                        f"\n  В деревне родился ребёнок. "
                        f"Его назвали {name}.",
                        GREEN
                    )
                )

        # ─────────────────────────────────────────────────────────────
        # КОНКУРЕНТ
        # ─────────────────────────────────────────────────────────────
        elif self.event_id == "rival":
            print(
                color(
                    "\n  В лесу вспыхнул второй алтарь.",
                    MAGENTA
                )
            )

            print(
                "  Кто-то ещё услышал молитвы этой долины."
            )

            god.secret_points += 1

            # Конкурент не наносит прямой урон.
            # Он создаёт долгосрочное давление.
            for v in village.villagers:
                if v.alive:
                    if random.random() < 0.25:
                        v.faith = clamp(v.faith - 8, 0, 100)

            village.morale = clamp(
                village.morale - 3,
                0,
                100
            )

        # ─────────────────────────────────────────────────────────────
        # ТОРГОВЫЙ КАРАВАН
        # ─────────────────────────────────────────────────────────────
        elif self.event_id == "caravan":
            village.gold += 12
            village.food += 10

            print(
                color(
                    "\n  Торговый караван прошёл через долину.",
                    GREEN
                )
            )
            print(
                "  Купцы оставили часть припасов за безопасную дорогу."
            )

        # ─────────────────────────────────────────────────────────────
        # ЗВЕЗДОПАД
        # ─────────────────────────────────────────────────────────────
        elif self.event_id == "stars":
            god.gain_faith(15)
            god.glory += 5
            god.secret_points += 2

            for v in village.villagers:
                if v.alive:
                    v.faith = clamp(v.faith + 5, 0, 100)
                    v.happiness = clamp(v.happiness + 5, 0, 100)

            print(
                color(
                    "\n  Ночью небо рассыпалось серебряными искрами.",
                    CYAN
                )
            )
            print(
                "  Люди сочли это добрым знаком."
            )

        print()


# ═════════════════════════════════════════════════════════════════════
# ИГРА
# ═════════════════════════════════════════════════════════════════════

class Game:

    def __init__(self):
        self.god = God()
        self.village = Village()

        self.running = True
        self.turn = 1

        self.message_log = []

        self.event_interval = 3

        self.names = [
            "Арина",
            "Борис",
            "Вера",
            "Глеб",
            "Дарья",
            "Егор",
            "Злата",
            "Илья",
            "Кира",
            "Лука",
            "Мирон",
            "Ника",
            "Олег",
            "Рада",
            "Савва",
            "Тая",
            "Фёдор",
            "Яна",
            "Марк",
            "Лея",
            "Роман",
            "Элина",
            "Степан",
            "Мила",
        ]

        self.used_names = set()

        self.professions = [
            "Фермер",
            "Фермер",
            "Дровосек",
            "Каменщик",
            "Торговец",
        ]

    # ═══════════════════════════════════════════════════════════════
    # НАЧАЛО ИГРЫ
    # ═══════════════════════════════════════════════════════════════

    def new_game(self):
        clear_screen()

        print(color(TEMPLE_ART, CYAN))

        print(
            color(
                "             В О З В Ы Ш Е Н Н Ы Й",
                BOLD
            )
        )
        print(
            color(
                "                  ПОСЛЕДНИЙ АЛТАРЬ",
                MAGENTA
            )
        )

        print()

        box([
            "Вы просыпаетесь в тишине, которую слышат только боги.",
            "",
            "Перед вами — маленькая долина.",
            "Деревня насчитывает несколько десятков душ.",
            "",
            "У них есть хлеб.",
            "Есть крыши над головой.",
            "Есть старый храм.",
            "",
            "Но больше всего им не хватает уверенности,",
            "что кто-то действительно слышит их молитвы.",
        ])

        print()

        name = input(
            color(
                "  Назовите себя, юное божество: ",
                YELLOW
            )
        ).strip()

        if not name:
            name = random.choice([
                "Безымянный",
                "Хранитель",
                "Смотрящий",
                "Тот-Кого-Ждут"
            ])

        self.god.name = name[:24]

        self.create_starting_village()

        # Небольшая вариативность старта.
        starting_type = random.choice([
            "rich",
            "poor",
            "balanced"
        ])

        if starting_type == "rich":
            self.village.food += 20
            self.village.wood += 10
            self.village.gold += 8

        elif starting_type == "poor":
            self.village.food -= 15
            self.village.wood -= 10
            self.god.faith += 12

        else:
            self.village.stone += 8

        print()

        box([
            f"Теперь вы — {self.god.name}.",
            "Ваш алтарь слаб, но ваша власть ещё только начинается.",
            "",
            "Люди не обязаны любить вас.",
            "Они даже не обязаны верить.",
            "",
            "Ваша задача — сделать так, чтобы к концу истории",
            "у этой долины всё ещё было будущее."
        ])

        pause()

    def create_starting_village(self):
        """Создаёт жителей первой деревни."""
        self.village.villagers.clear()
        self.used_names.clear()

        starting = [
            ("Арина", 34, "Фермер"),
            ("Борис", 42, "Дровосек"),
            ("Вера", 28, "Фермер"),
            ("Глеб", 51, "Каменщик"),
            ("Кира", 31, "Торговец"),
            ("Мирон", 23, "Фермер"),
            ("Злата", 46, "Фермер"),
            ("Лука", 39, "Жрец"),
            ("Рада", 19, "Ученик"),
            ("Егор", 27, "Дровосек"),
        ]

        for name, age, profession in starting:
            villager = Villager(
                name=name,
                age=age,
                profession=profession,
                happiness=random.randint(55, 75),
                faith=random.randint(45, 75),
                health=random.randint(75, 100)
            )

            self.village.add_villager(villager)
            self.used_names.add(name)

    def available_names(self):
        """Возвращает ещё не использованные имена."""
        return [
            name
            for name in self.names
            if name not in self.used_names
        ]

    # ═══════════════════════════════════════════════════════════════
    # ГЛАВНЫЙ ЦИКЛ
    # ═══════════════════════════════════════════════════════════════

    def run(self):
        self.introduction_menu()

        while self.running:
            if self.check_endings():
                break

            clear_screen()
            self.main_screen()

            choice = input(
                color(
                    "\n  Выберите действие → ",
                    YELLOW
                )
            ).strip()

            self.handle_choice(choice)

    def introduction_menu(self):
        """Меню первого запуска."""
        while True:
            clear_screen()

            print(color(TEMPLE_ART, CYAN))

            title("ВОЗВЫШЕННЫЙ: ПОСЛЕДНИЙ АЛТАРЬ")

            print(
                "\n  [1] Новая игра"
                "\n  [2] Загрузить сохранение"
                "\n  [3] Управление"
                "\n  [0] Выход"
            )

            choice = input("\n  > ").strip()

            if choice == "1":
                self.new_game()
                return

            if choice == "2":
                if self.load_game():
                    pause()
                    return

                pause()

            elif choice == "3":
                self.show_help()
                pause()

            elif choice == "0":
                self.running = False
                return

    # ═══════════════════════════════════════════════════════════════
    # ГЛАВНЫЙ ЭКРАН
    # ═══════════════════════════════════════════════════════════════

    def main_screen(self):
        print(color(VILLAGE_ART, CYAN))

        print(
            color(
                f"  {self.god.name}",
                BOLD
            )
        )

        print(
            f"  {self.village.name}  •  "
            f"{self.village.season_name()}, "
            f"год {self.village.year}"
        )

        print()

        print(
            color(
                f"  ✦ Вера       {self.god.faith:>4}",
                MAGENTA
            )
        )

        print(
            f"    Благосклонность  {self.god.favor:>3}/100"
        )

        print(
            f"    Слава            {self.god.glory:>3}"
        )

        print()

        print(
            f"  Население: {self.village.population():>2}    "
            f"Счастье: {self.village.average_happiness():>3}/100"
        )

        print(
            f"  Вера жителей: {self.village.average_faith():>3}/100    "
            f"Больных: {self.village.sick_count()}"
        )

        print()

        print(
            f"  Еда       {self.village.food:>4}  "
            f"{bar(self.village.food, 150)}"
        )

        print(
            f"  Дерево    {self.village.wood:>4}  "
            f"{bar(self.village.wood, 150)}"
        )

        print(
            f"  Камень    {self.village.stone:>4}  "
            f"{bar(self.village.stone, 150)}"
        )

        print(
            f"  Золото    {self.village.gold:>4}  "
            f"{bar(self.village.gold, 100)}"
        )

        print()

        print(
            f"  Храм: уровень {self.village.temple_level}/7"
        )

        print()

        print(color("  ┌─ Действия ─────────────────────────────────────────────┐", CYAN))

        print("  │  1. Состояние деревни        6. Завершить ход         │")
        print("  │  2. Жители                   7. Сохранить              │")
        print("  │  3. Чудеса                   8. Загрузить              │")
        print("  │  4. Алтарь и дары            9. Справка                │")
        print("  │  5. Улучшить храм            0. Выйти                  │")

        print(color("  └─────────────────────────────────────────────────────────┘", CYAN))

    # ═══════════════════════════════════════════════════════════════
    # ДЕЙСТВИЯ
    # ═══════════════════════════════════════════════════════════════

    def handle_choice(self, choice):
        if choice == "1":
            self.show_village()

        elif choice == "2":
            self.show_villagers()

        elif choice == "3":
            self.miracle_menu()

        elif choice == "4":
            self.altar_menu()

        elif choice == "5":
            self.upgrade_temple_menu()

        elif choice == "6":
            self.end_turn()

        elif choice == "7":
            self.save_game()

        elif choice == "8":
            self.load_game()

        elif choice == "9":
            self.show_help()

        elif choice == "0":
            self.exit_game()

        else:
            print(
                color(
                    "\n  Неизвестная команда.",
                    YELLOW
                )
            )
            pause()

    # ═══════════════════════════════════════════════════════════════
    # СОСТОЯНИЕ ДЕРЕВНИ
    # ═══════════════════════════════════════════════════════════════

    def show_village(self):
        clear_screen()

        title("СОСТОЯНИЕ ДЕРЕВНИ")

        print(color(VILLAGE_ART, CYAN))

        print(
            f"  {self.village.name}"
        )

        print(
            f"  {self.village.season_name()}, "
            f"год {self.village.year}"
        )

        print()

        print(
            f"  Население:       {self.village.population()}"
        )

        print(
            f"  Среднее счастье: {self.village.average_happiness()}/100"
        )

        print(
            f"  Средняя вера:    {self.village.average_faith()}/100"
        )

        print(
            f"  Больные:          {self.village.sick_count()}"
        )

        print(
            f"  Мораль:           {self.village.morale}/100"
        )

        print()

        print(color("  РЕСУРСЫ", BOLD))

        print(
            f"  Еда:    {self.village.food}"
            f"\n  Дерево: {self.village.wood}"
            f"\n  Камень: {self.village.stone}"
            f"\n  Золото: {self.village.gold}"
        )

        print()

        production = self.village.production()

        print(color("  ПРОИЗВОДСТВО ЗА ХОД", BOLD))

        print(
            f"  +{production[0]} еды"
            f"\n  +{production[1]} дерева"
            f"\n  +{production[2]} камня"
            f"\n  +{production[3]} золота"
        )

        print()

        print(color("  ИСТОРИЯ БОЖЕСТВА", BOLD))

        print(
            f"  Чудес совершено:     {self.god.miracles_used}"
        )

        print(
            f"  Молитв услышано:     {self.god.answered_prayers}"
        )

        print(
            f"  Молитв проигнорировано: {self.god.ignored_prayers}"
        )

        print(
            f"  Пережито бедствий:    "
            f"{self.village.disasters_survived}"
        )

        pause()

    # ═══════════════════════════════════════════════════════════════
    # ЖИТЕЛИ
    # ═══════════════════════════════════════════════════════════════

    def show_villagers(self):
        while True:
            clear_screen()

            title("ЖИТЕЛИ ЛУННОЙ ДОЛИНЫ")

            alive = [
                v
                for v in self.village.villagers
                if v.alive
            ]

            for index, villager in enumerate(alive, 1):
                status = (
                    color("БОЛЕН", RED)
                    if villager.sick
                    else color("здоров", GREEN)
                )

                print(
                    f"  {index:>2}. "
                    f"{villager.name:<10} "
                    f"{villager.age:>2} лет  "
                    f"{villager.profession:<10} "
                    f"❤ {villager.health:>3}  "
                    f"☀ {villager.happiness:>3}  "
                    f"✦ {villager.faith:>3}  "
                    f"{status}"
                )

            print()

            print(
                color(
                    "  Выберите жителя для подробностей или 0 для выхода.",
                    DIM
                )
            )

            choice = input("\n  > ").strip()

            if choice == "0":
                return

            try:
                index = int(choice) - 1

                if 0 <= index < len(alive):
                    self.villager_details(alive[index])
                else:
                    raise ValueError

            except ValueError:
                print(color("  Неверный номер.", YELLOW))
                pause()

    def villager_details(self, villager):
        clear_screen()

        title(villager.name.upper())

        icon = "☠" if villager.health <= 20 else "☻"

        print(
            f"\n  {icon} {villager.name}"
            f"\n  Возраст: {villager.age}"
            f"\n  Профессия: {villager.profession}"
        )

        print()

        print(
            f"  Здоровье:  {villager.health}/100"
            f"\n  Счастье:   {villager.happiness}/100"
            f"\n  Вера:      {villager.faith}/100"
        )

        print()

        print(
            f"  Настроение: {villager.mood()}"
        )

        print(
            f"  Вера: {villager.faith_description()}"
        )

        if villager.sick:
            print(
                color(
                    "\n  Этот человек болен и нуждается в помощи.",
                    RED
                )
            )

        print()

        print(
            color(
                "  Бог может говорить с людьми во сне.",
                DIM
            )
        )

        pause()

    # ═══════════════════════════════════════════════════════════════
    # ЧУДЕСА
    # ═══════════════════════════════════════════════════════════════

    def miracle_menu(self):
        while True:
            clear_screen()

            title("ЧУДЕСА")

            print(
                f"  Вера божества: {color(str(self.god.faith), MAGENTA)}"
            )

            print()

            miracles = [
                ("1", "Благословить урожай", 12),
                ("2", "Послать дождь", 16),
                ("3", "Исцелить больного", 20),
                ("4", "Явить знамение", 8),
                ("5", "Говорить во сне", 10),
                ("6", "Защитить деревню", 25),
                ("7", "Напугать врагов", 18),
                ("8", "Великий урожай", 40),
            ]

            descriptions = {
                1: "Урожай этого сезона будет щедрее.",
                2: "Вода наполнит пересохшие ручьи.",
                3: "Болезнь отступит от одного жителя.",
                4: "Небольшое знамение укрепит веру.",
                5: "Вы поговорите с одним человеком во сне.",
                6: "Ближайшее бедствие будет ослаблено.",
                7: "Опасные люди дважды подумают, прежде чем напасть.",
                8: "Сильнейшее чудо. Но цена его огромна.",
            }

            for number, name, cost in miracles:
                available = self.god.faith >= cost
                mark = color("✓", GREEN) if available else color("×", RED)

                print(
                    f"  [{number}] {mark} "
                    f"{name:<24} "
                    f"Цена: {cost:>2} веры"
                )

            print("\n  [0] Назад")

            choice = input("\n  > ").strip()

            if choice == "0":
                return

            if choice.isdigit() and 1 <= int(choice) <= 8:
                miracle_id = int(choice)

                print()
                print(
                    color(
                        descriptions[miracle_id],
                        CYAN
                    )
                )

                self.perform_miracle(miracle_id)

                pause()

            else:
                print(color("  Нет такого чуда.", YELLOW))
                pause()

    def perform_miracle(self, miracle_id):
        costs = {
            1: 12,
            2: 16,
            3: 20,
            4: 8,
            5: 10,
            6: 25,
            7: 18,
            8: 40
        }

        cost = costs[miracle_id]

        if not self.god.spend_faith(cost):
            print(
                color(
                    "\n  Алтарь молчит.",
                    RED
                )
            )

            print(
                "  У вас недостаточно веры."
            )

            return

        self.god.miracles_used += 1
        self.village.total_blessings += 1

        # ─────────────────────────────────────────────────────────
        # БЛАГОСЛОВИТЬ УРОЖАЙ
        # ─────────────────────────────────────────────────────────

        if miracle_id == 1:
            amount = 30 + self.village.temple_level * 5
            self.village.food += amount

            self.village.morale = clamp(
                self.village.morale + 4,
                0,
                100
            )

            for v in self.village.villagers:
                if v.alive:
                    v.happiness = clamp(
                        v.happiness + 3,
                        0,
                        100
                    )
                    v.faith = clamp(
                        v.faith + 2,
                        0,
                        100
                    )

            self.god.glory += 2

            print(
                color(
                    f"\n  Золотистый свет прошёл над полями.",
                    GREEN
                )
            )

            print(
                f"  Деревня получила +{amount} еды."
            )

        # ─────────────────────────────────────────────────────────
        # ДОЖДЬ
        # ─────────────────────────────────────────────────────────

        elif miracle_id == 2:
            self.village.food += 20
            self.village.wood += 5

            for v in self.village.villagers:
                if v.alive:
                    v.happiness = clamp(
                        v.happiness + 4,
                        0,
                        100
                    )

            self.god.glory += 3

            print(
                color(
                    "\n  Сначала упала одна капля.",
                    CYAN
                )
            )
            print(
                "  Затем небо раскрылось."
            )

        # ─────────────────────────────────────────────────────────
        # ИСЦЕЛЕНИЕ
        # ─────────────────────────────────────────────────────────

        elif miracle_id == 3:
            sick = [
                v for v in self.village.villagers
                if v.alive and v.sick
            ]

            if not sick:
                self.god.gain_faith(5)

                print(
                    color(
                        "\n  Никого больного не оказалось.",
                        YELLOW
                    )
                )

                print(
                    "  Люди восприняли это как знак вашей заботы."
                )

                return

            target = min(
                sick,
                key=lambda v: v.health
            )

            target.sick = False
            target.health = clamp(
                target.health + 55,
                0,
                100
            )
            target.happiness = clamp(
                target.happiness + 20,
                0,
                100
            )
            target.faith = clamp(
                target.faith + 20,
                0,
                100
            )

            self.god.glory += 5
            self.god.mercy += 2
            self.god.answered_prayers += 1

            print(
                color(
                    f"\n  Вы коснулись сна {target.name}.",
                    GREEN
                )
            )

            print(
                f"  Утром болезнь исчезла."
            )

        # ─────────────────────────────────────────────────────────
        # ЗНАМЕНИЕ
        # ─────────────────────────────────────────────────────────

        elif miracle_id == 4:
            gain = 8 + self.village.temple_level * 2

            for v in self.village.villagers:
                if v.alive:
                    v.faith = clamp(
                        v.faith + 5,
                        0,
                        100
                    )

            self.god.glory += 4

            print(
                color(
                    "\n  На вершине храма вспыхнул белый огонь.",
                    CYAN
                )
            )

            print(
                f"  Вера жителей укрепилась."
            )

        # ─────────────────────────────────────────────────────────
        # СОН
        # ─────────────────────────────────────────────────────────

        elif miracle_id == 5:
            alive = [
                v for v in self.village.villagers
                if v.alive
            ]

            if not alive:
                return

            target = random.choice(alive)

            dreams = [
                "Он увидел спокойную реку.",
                "Она услышала колокола в далёком храме.",
                "Ему приснилось дерево, корни которого уходили в небо.",
                "Она увидела маленький огонь, который не гас даже под дождём.",
                "Ему показалась дверь, за которой стояло утро."
            ]

            target.faith = clamp(
                target.faith + 15,
                0,
                100
            )

            target.happiness = clamp(
                target.happiness + 10,
                0,
                100
            )

            self.god.secret_points += 1

            print(
                color(
                    f"\n  Этой ночью {target.name} видел вас.",
                    MAGENTA
                )
            )

            print(
                f"  {random.choice(dreams)}"
            )

        # ─────────────────────────────────────────────────────────
        # ЗАЩИТА
        # ─────────────────────────────────────────────────────────

        elif miracle_id == 6:
            self.village.morale = clamp(
                self.village.morale + 10,
                0,
                100
            )

            for v in self.village.villagers:
                if v.alive:
                    v.happiness = clamp(
                        v.happiness + 5,
                        0,
                        100
                    )

            self.god.glory += 5
            self.god.secret_points += 1

            print(
                color(
                    "\n  Тень огромных крыльев легла на долину.",
                    CYAN
                )
            )

            print(
                "  Этой ночью деревня может спать спокойно."
            )

        # ─────────────────────────────────────────────────────────
        # НАПУГАТЬ ВРАГОВ
        # ─────────────────────────────────────────────────────────

        elif miracle_id == 7:
            self.god.wrath += 3
            self.god.glory += 4
            self.village.morale = clamp(
                self.village.morale + 3,
                0,
                100
            )

            print(
                color(
                    "\n  Вдалеке прогремел голос грома.",
                    RED
                )
            )

            print(
                "  Никто не решился приблизиться к деревне."
            )

        # ─────────────────────────────────────────────────────────
        # ВЕЛИКИЙ УРОЖАЙ
        # ─────────────────────────────────────────────────────────

        elif miracle_id == 8:
            amount = 100 + self.village.temple_level * 10

            self.village.food += amount

            self.god.glory += 10
            self.god.secret_points += 2

            for v in self.village.villagers:
                if v.alive:
                    v.faith = clamp(
                        v.faith + 8,
                        0,
                        100
                    )
                    v.happiness = clamp(
                        v.happiness + 8,
                        0,
                        100
                    )

            print(
                color(
                    "\n  Поля вспыхнули золотом.",
                    GREEN
                )
            )

            print(
                f"  Собрано невероятное количество урожая: +{amount} еды."
            )

        self.village.morale = clamp(
            self.village.morale,
            0,
            100
        )

    # ═══════════════════════════════════════════════════════════════
    # АЛТАРЬ
    # ═══════════════════════════════════════════════════════════════

    def altar_menu(self):
        while True:
            clear_screen()

            title("АЛТАРЬ")

            print(color(TEMPLE_ART, CYAN))

            print(
                f"  Уровень храма: {self.village.temple_level}"
            )

            print(
                f"  Вера божества: {self.god.faith}"
            )

            print()

            print(
                "  Жители каждый ход молятся самостоятельно."
            )

            print(
                "  Здесь же они оставляют дары."
            )

            print()

            print(
                "  [1] Собрать дары"
                "\n  [2] Вознести общую молитву"
                "\n  [3] Осмотреть храм"
                "\n  [0] Назад"
            )

            choice = input("\n  > ").strip()

            if choice == "0":
                return

            if choice == "1":
                self.collect_offerings()
                pause()

            elif choice == "2":
                self.collect_prayer()
                pause()

            elif choice == "3":
                self.inspect_temple()
                pause()

            else:
                print(color("  Нет такого действия.", YELLOW))
                pause()

    def collect_offerings(self):
        """
        Случайный сбор даров.

        Чем выше счастье и вера жителей,
        тем больше ожидаемая ценность.
        """
        faith = self.village.average_faith()
        happiness = self.village.average_happiness()

        base = self.village.population() // 2
        bonus = (faith + happiness) // 25

        amount = max(
            1,
            base + bonus + random.randint(0, 6)
        )

        self.god.gain_faith(amount)
        self.village.total_sacrifices += 1

        print(
            color(
                "\n  На камне алтаря остались хлеб, зерно, монеты.",
                YELLOW
            )
        )

        print(
            f"  Ваша вера увеличилась на {amount}."
        )

    def collect_prayer(self):
        amount = 3 + (
            self.village.average_faith() // 20
        ) + (
            self.village.temple_level
        )

        self.god.gain_faith(amount)
        self.god.answered_prayers += 1

        print(
            color(
                "\n  Над долиной поднялся тихий хор.",
                CYAN
            )
        )

        print(
            f"  Молитвы дали вам {amount} веры."
        )

    def inspect_temple(self):
        print(color(TEMPLE_ART, CYAN))

        print(
            f"\n  Уровень: {self.village.temple_level}/7"
        )

        bonus = self.village.temple_level * 2

        print(
            f"  Бонус к молитвам: +{bonus}"
        )

        print(
            f"  Архитектура: "
            f"{self.temple_description()}"
        )

    def temple_description(self):
        descriptions = {
            1: "старый каменный алтарь",
            2: "небольшая часовня",
            3: "крепкий деревенский храм",
            4: "светлый храм с колоколами",
            5: "высокое святилище",
            6: "великий храм долины",
            7: "место, где небо касается земли",
        }

        return descriptions[self.village.temple_level]

    # ═══════════════════════════════════════════════════════════════
    # УЛУЧШЕНИЕ ХРАМА
    # ═══════════════════════════════════════════════════════════════

    def upgrade_temple_menu(self):
        clear_screen()

        title("ХРАМ")

        if self.village.temple_level >= 7:
            print(
                color(
                    "\n  Ваш храм уже достиг предела.",
                    GREEN
                )
            )
            pause()
            return

        cost = self.village.temple_upgrade_cost()

        print(
            f"\n  Текущий уровень: "
            f"{self.village.temple_level}"
        )

        print(
            f"  Следующий уровень: "
            f"{self.village.temple_level + 1}"
        )

        print()

        print(
            "  Цена:"
            f"\n  Дерево: {cost['wood']}"
            f"\n  Камень: {cost['stone']}"
            f"\n  Золото: {cost['gold']}"
        )

        print()

        if self.village.can_upgrade_temple():
            choice = input(
                "  Построить? [y/n] → "
            ).strip().lower()

            if choice in ("y", "yes", "д", "да"):
                success, message = (
                    self.village.upgrade_temple()
                )

                if success:
                    self.god.glory += 5

                print(
                    color(
                        f"\n  {message}",
                        GREEN if success else RED
                    )
                )

            else:
                print("\n  Строительство отменено.")

        else:
            print(
                color(
                    "\n  Ресурсов недостаточно.",
                    RED
                )
            )

        pause()

    # ═══════════════════════════════════════════════════════════════
    # ХОД
    # ═══════════════════════════════════════════════════════════════

    def end_turn(self):
        clear_screen()

        title(
            f"ХОД {self.turn} • "
            f"{self.village.season_name()}, "
            f"год {self.village.year}"
        )

        print(
            color(
                "  Мир продолжает жить без остановки.",
                DIM
            )
        )

        print()

        # ─────────────────────────────────────────────────────────
        # ПРОИЗВОДСТВО
        # ─────────────────────────────────────────────────────────

        production = self.village.production()

        self.village.food += production[0]
        self.village.wood += production[1]
        self.village.stone += production[2]
        self.village.gold += production[3]

        print(
            f"  Производство: "
            f"+{production[0]} еды, "
            f"+{production[1]} дерева, "
            f"+{production[2]} камня, "
            f"+{production[3]} золота."
        )

        # ─────────────────────────────────────────────────────────
        # ПОТРЕБЛЕНИЕ
        # ─────────────────────────────────────────────────────────

        fed, value = self.village.consume_food()

        if fed:
            print(
                color(
                    f"  Жители съели {value} единиц еды.",
                    GREEN
                )
            )
        else:
            print(
                color(
                    "  Запасов еды не хватило.",
                    RED
                )
            )

            self.god.faith = max(
                0,
                self.god.faith - 3
            )

        # ─────────────────────────────────────────────────────────
        # ЕСТЕСТВЕННАЯ ВЕРА
        # ─────────────────────────────────────────────────────────

        faith_gain = sum(
            v.daily_faith()
            for v in self.village.villagers
            if v.alive
        )

        temple_bonus = self.village.temple_level

        # Если деревня несчастна, вера растёт хуже.
        if self.village.morale < 35:
            faith_gain //= 2

        faith_gain += temple_bonus

        self.god.gain_faith(faith_gain)

        print(
            color(
                f"  Молитвы принесли +{faith_gain} веры.",
                MAGENTA
            )
        )

        # ─────────────────────────────────────────────────────────
        # МОРАЛЬ
        # ─────────────────────────────────────────────────────────

        avg_happiness = self.village.average_happiness()

        if avg_happiness >= 75:
            self.village.morale = clamp(
                self.village.morale + 2,
                0,
                100
            )

        elif avg_happiness < 40:
            self.village.morale = clamp(
                self.village.morale - 3,
                0,
                100
            )

        # ─────────────────────────────────────────────────────────
        # ЖИЗНЬ ЖИТЕЛЕЙ
        # ─────────────────────────────────────────────────────────

        self.update_villagers()

        # ─────────────────────────────────────────────────────────
        # СЕЗОН
        # ─────────────────────────────────────────────────────────

        old_year = self.village.year

        self.village.seasonal_change()

        if self.village.year != old_year:
            print()
            print(
                color(
                    f"  ✦ Начался {self.village.year}-й год.",
                    CYAN
                )
            )

            self.yearly_effects()

        # ─────────────────────────────────────────────────────────
        # СОБЫТИЕ
        # ─────────────────────────────────────────────────────────

        self.turn += 1

        if self.turn % self.event_interval == 0:
            self.trigger_random_event()

        print()

        print(
            color(
                "  Ход завершён.",
                GREEN
            )
        )

        pause()

    def update_villagers(self):
        """
        Каждый ход жители стареют, лечатся или теряют настроение.
        """

        for v in self.village.villagers:
            if not v.alive:
                continue

            # Лёгкое естественное восстановление.
            if not v.sick:
                v.health = clamp(
                    v.health + random.randint(0, 2),
                    0,
                    100
                )

            else:
                # Без лечения болезнь иногда проходит сама.
                if random.random() < 0.12:
                    v.sick = False
                    v.health = clamp(
                        v.health + 8,
                        0,
                        100
                    )

            # Вера слегка движется вслед за счастьем.
            if v.happiness > 75:
                v.faith = clamp(
                    v.faith + 1,
                    0,
                    100
                )

            elif v.happiness < 30:
                v.faith = clamp(
                    v.faith - 2,
                    0,
                    100
                )

            # Очень низкая вера постепенно снижает счастье.
            if v.faith < 20:
                v.happiness = clamp(
                    v.happiness - 2,
                    0,
                    100
                )

            # Маленькая вероятность естественного изменения настроения.
            v.happiness = clamp(
                v.happiness + random.choice([-1, 0, 0, 1]),
                0,
                100
            )

        # Несчастные жители иногда покидают деревню.
        self.check_departures()

    def check_departures(self):
        unhappy = [
            v
            for v in self.village.villagers
            if v.alive and v.happiness <= 12
        ]

        if unhappy and random.random() < 0.25:
            victim = random.choice(unhappy)

            victim.alive = False

            print(
                color(
                    f"\n  {victim.name} покинул деревню.",
                    RED
                )
            )

            print(
                "  Его вера оказалась слишком слабой."
            )

            self.god.ignored_prayers += 1

    def yearly_effects(self):
        """
        В начале нового года растёт сложность.
        """
        # Зима оставляет последствия.
        for v in self.village.villagers:
            if v.alive and random.random() < 0.08:
                v.health = clamp(
                    v.health - 5,
                    0,
                    100
                )

        # С каждым годом события становятся чуть опаснее.
        self.event_interval = max(
            2,
            4 - self.village.year // 3
        )

        # Старение.
        for v in self.village.villagers:
            if v.alive and v.age > 0:
                v.age += 1

    # ═══════════════════════════════════════════════════════════════
    # СЛУЧАЙНЫЕ СОБЫТИЯ
    # ═══════════════════════════════════════════════════════════════

    def trigger_random_event(self):
        events = [
            Event(
                "Сухой ветер",
                "Несколько недель над полями висело медное небо.",
                "drought"
            ),
            Event(
                "Волки у амбара",
                "Ночью в деревню пришли голодные волки.",
                "wolves"
            ),
            Event(
                "Серая лихорадка",
                "Утром несколько жителей проснулись с жаром.",
                "plague"
            ),
            Event(
                "Странник",
                "Пыльный путник остановился возле вашего храма.",
                "traveler"
            ),
            Event(
                "Новый голос",
                "Из одного дома донёсся первый плач ребёнка.",
                "birth"
            ),
            Event(
                "Чужой алтарь",
                "На северной окраине леса кто-то поставил каменный алтарь.",
                "rival"
            ),
            Event(
                "Торговый караван",
                "К дороге приблизились телеги с гербами купеческого дома.",
                "caravan"
            ),
            Event(
                "Ночь падающих звёзд",
                "Небо этой ночью оказалось слишком ярким.",
                "stars"
            )
        ]

        # Некоторые события становятся чаще с течением времени.
        weights = []

        for event in events:
            weight = 10

            if self.village.year >= 3:
                if event.event_id in ("drought", "plague", "rival"):
                    weight += 5

            if self.village.year >= 5:
                if event.event_id in ("drought", "plague"):
                    weight += 8

            weights.append(weight)

        event = random.choices(
            events,
            weights=weights,
            k=1
        )[0]

        if event.event_id in (
            "drought",
            "wolves",
            "plague",
            "rival"
        ):
            self.village.disasters_survived += 1

        event.trigger(self)

    # ═══════════════════════════════════════════════════════════════
    # КОНЦОВКИ
    # ═══════════════════════════════════════════════════════════════

    def check_endings(self):
        """
        Проверяет условия окончания.

        Есть:
            - плохая
            - нейтральная
            - хорошая
            - секретная

        Игра не заканчивается просто от одного плохого события.
        Система требует устойчивого результата.
        """

        population = self.village.population()
        avg_faith = self.village.average_faith()
        avg_happiness = self.village.average_happiness()

        # ПЛОХАЯ КОНЦОВКА
        if population <= 2 or (
            self.village.morale <= 5 and avg_faith <= 10
        ):
            self.bad_ending()
            return True

        # ХОРОШАЯ КОНЦОВКА
        if (
            self.village.year >= 8
            and population >= 12
            and avg_faith >= 75
            and avg_happiness >= 70
            and self.village.temple_level >= 5
        ):
            self.good_ending()
            return True

        # СЕКРЕТНАЯ КОНЦОВКА
        if (
            self.village.year >= 6
            and self.god.secret_points >= 8
            and self.god.mercy >= 5
            and self.god.wrath == 0
            and self.village.temple_level >= 6
        ):
            self.secret_ending()
            return True

        # НЕЙТРАЛЬНАЯ
        if self.village.year >= 12:
            self.neutral_ending()
            return True

        return False

    def bad_ending(self):
        clear_screen()

        title("КОНЕЦ • ПУСТОЙ АЛТАРЬ")

        print(color(TEMPLE_ART, RED))

        box([
            "Последняя молитва стихла.",
            "",
            "Люди перестали смотреть в сторону храма.",
            "Кто-то ушёл на восток.",
            "Кто-то остался, но больше ничего не ждал.",
            "",
            "Камень алтаря остался холодным.",
            "",
            "Вы были богом этой долины.",
            "Но не сумели стать её надеждой."
        ])

        print(
            color(
                "\n  Ваша история закончилась.",
                RED
            )
        )

        pause()

    def neutral_ending(self):
        clear_screen()

        title("КОНЕЦ • ТИХАЯ ДОЛИНА")

        print(color(VILLAGE_ART, CYAN))

        box([
            "Годы прошли.",
            "",
            "Деревня выжила.",
            "Не стала богатой.",
            "Не стала легендой.",
            "",
            "Но дети всё ещё знают старую молитву.",
            "По вечерам в храме горит маленькая свеча.",
            "",
            "Возможно, этого достаточно."
        ])

        print(
            color(
                f"\n  Слава божества: {self.god.glory}",
                CYAN
            )
        )

        pause()

    def good_ending(self):
        clear_screen()

        title("КОНЕЦ • ЗОЛОТОЙ ВЕК")

        print(color(TEMPLE_ART, GREEN))

        box([
            "Прошло восемь лет.",
            "",
            "Там, где когда-то стояли три старых дома,",
            "теперь шумит большая деревня.",
            "",
            "Дети бегают по площади.",
            "Фермеры возвращаются с полей.",
            "Колокола храма слышны далеко за лесом.",
            "",
            "Люди верят в вас.",
            "",
            "Но важнее другое:",
            "они научились верить друг в друга."
        ])

        print(
            color(
                "\n  Вы стали не просто богом.",
                GREEN
            )
        )

        print(
            color(
                "  Вы стали хранителем.",
                BOLD
            )
        )

        pause()

    def secret_ending(self):
        clear_screen()

        title("СЕКРЕТНАЯ КОНЦОВКА • ПЕРВАЯ ЗАРЯ")

        print(
            color(
                r"""
                         *
                       \ | /
                    --  ☼  --
                       / | \

                     /\   /\
                    /  \_/  \
                   /       \
                """,
                MAGENTA
            )
        )

        box([
            "Вы никогда не требовали поклонения.",
            "Не посылали гром.",
            "Не карали сомневающихся.",
            "",
            "Вы отвечали на молитвы тихо.",
            "",
            "И однажды жители поняли:",
            "бог, которого они искали, всё это время",
            "учил их самостоятельно хранить свой свет.",
            "",
            "В то утро никто не принёс даров.",
            "",
            "И впервые вы не почувствовали голода.",
            "",
            "Потому что вера стала частью самой долины."
        ])

        print(
            color(
                "\n  Вы больше не нуждаетесь в поклонении.",
                MAGENTA
            )
        )

        print(
            color(
                "  Вы стали чем-то большим, чем бог.",
                BOLD
            )
        )

        pause()

    # ═══════════════════════════════════════════════════════════════
    # СОХРАНЕНИЕ
    # ═══════════════════════════════════════════════════════════════

    def save_game(self):
        """
        Сохраняет всю игру в JSON.

        Используется временный файл, чтобы снизить риск
        повреждения основного сохранения при неожиданном закрытии.
        """
        data = {
            "god": self.god.to_dict(),
            "village": self.village.to_dict(),
            "turn": self.turn,
            "event_interval": self.event_interval,
            "used_names": list(self.used_names)
        }

        temp_file = SAVE_FILE + ".tmp"

        try:
            with open(
                temp_file,
                "w",
                encoding="utf-8"
            ) as file:
                json.dump(
                    data,
                    file,
                    ensure_ascii=False,
                    indent=2
                )

            os.replace(
                temp_file,
                SAVE_FILE
            )

            print(
                color(
                    "\n  ✦ Игра сохранена.",
                    GREEN
                )
            )

        except (OSError, TypeError) as error:
            print(
                color(
                    f"\n  Не удалось сохранить игру: {error}",
                    RED
                )
            )

        pause()

    def load_game(self):
        """
        Загружает игру.

        Повреждённый файл не должен ронять программу.
        """
        if not os.path.exists(SAVE_FILE):
            print(
                color(
                    "\n  Сохранение не найдено.",
                    YELLOW
                )
            )
            return False

        try:
            with open(
                SAVE_FILE,
                "r",
                encoding="utf-8"
            ) as file:
                data = json.load(file)

            self.god = God.from_dict(
                data["god"]
            )

            self.village = Village.from_dict(
                data["village"]
            )

            self.turn = int(
                data.get("turn", 1)
            )

            self.event_interval = int(
                data.get("event_interval", 3)
            )

            self.used_names = set(
                data.get("used_names", [])
            )

            print(
                color(
                    "\n  ✦ Сохранение загружено.",
                    GREEN
                )
            )

            return True

        except (
            OSError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError
        ) as error:

            print(
                color(
                    f"\n  Сохранение повреждено или имеет "
                    f"неверный формат: {error}",
                    RED
                )
            )

            return False

    # ═══════════════════════════════════════════════════════════════
    # СПРАВКА
    # ═══════════════════════════════════════════════════════════════

    def show_help(self):
        clear_screen()

        title("КАК ИГРАТЬ")

        box([
            "Вы управляете молодой силой, связанной с одной деревней.",
            "",
            "Главный ресурс — ВЕРА.",
            "Без неё чудеса невозможны.",
            "",
            "Но вера не появляется из воздуха.",
            "Люди должны быть счастливы, здоровы и иметь надежду.",
            "",
            "Ресурсы позволяют деревне выживать.",
            "Храм усиливает молитвы.",
            "Чудеса помогают людям, но стоят веры.",
            "",
            "Не обязательно спасать всех.",
            "Но каждое решение меняет дальнейшее состояние долины."
        ])

        print()

        print(color("  РЕСУРСЫ", BOLD))

        print(
            "  ✦ Вера   — энергия для чудес."
            "\n  🍞 Еда   — необходима жителям."
            "\n  🪵 Дерево — строительство."
            "\n  ◆ Камень — строительство храма."
            "\n  ◈ Золото — редкие улучшения."
        )

        print()

        print(color("  ВАЖНЫЕ ПОКАЗАТЕЛИ", BOLD))

        print(
            "  Счастье — влияет на производство и веру."
            "\n  Вера жителей — определяет силу молитв."
            "\n  Мораль — показывает общее настроение."
            "\n  Благосклонность — отношение людей к божеству."
        )

        print()

        print(color("  СТРАТЕГИИ", BOLD))

        print(
            "  • Милосердный бог — лечите и помогайте."
            "\n  • Хранитель — вкладывайтесь в храм и защиту."
            "\n  • Практичный бог — развивайте ресурсы."
            "\n  • Таинственный путь — используйте сны и знамения."
        )

        print()

        print(
            color(
                "  Игра не требует идеального решения каждого хода.",
                DIM
            )
        )

        pause()

    # ═══════════════════════════════════════════════════════════════
    # ВЫХОД
    # ═══════════════════════════════════════════════════════════════

    def exit_game(self):
        clear_screen()

        title("ПОКИНУТЬ ДОЛИНУ")

        print(
            "\n  Сохранить игру перед выходом?"
        )

        print(
            "\n  [1] Да"
            "\n  [2] Нет"
            "\n  [3] Отмена"
        )

        choice = input("\n  > ").strip()

        if choice == "1":
            self.save_game()
            self.running = False

        elif choice == "2":
            self.running = False

        else:
            return


# ═════════════════════════════════════════════════════════════════════
# ТОЧКА ВХОДА
# ═════════════════════════════════════════════════════════════════════

def main():
    """
    Точка входа.

    Дополнительный try/except нужен, чтобы неожиданные ошибки
    не превращались в непонятный вылет программы.
    """
    try:
        game = Game()
        game.run()

    except KeyboardInterrupt:
        print(
            color(
                "\n\n  Игра прервана пользователем.",
                YELLOW
            )
        )

    except EOFError:
        print(
            color(
                "\n\n  Ввод завершён.",
                YELLOW
            )
        )

    except Exception as error:
        print(
            color(
                "\n\n  Произошла непредвиденная ошибка:",
                RED
            )
        )

        print(
            color(
                f"  {type(error).__name__}: {error}",
                RED
            )
        )

        print(
            "\n  Если ошибка повторяется, проверьте версию Python."
        )


if __name__ == "__main__":
    main()