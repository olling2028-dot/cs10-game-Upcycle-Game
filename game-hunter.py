"""Hunter & Ollin serious game MVP.

This version turns the design doc into a small playable vertical slice:
- Move through the building
- Fight enemies with basic attacks
- Pick outfits after each floor
- Balance power vs sustainability tradeoffs
- Defeat the CEO boss to win
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import arcade

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
SCREEN_TITLE = "Hunter & Ollin - Upcycle Game MVP"

PLAYER_SPEED = 5
ATTACK_COOLDOWN = 0.25
ATTACK_RANGE = 70
ATTACK_DAMAGE = 18
BASE_PLAYER_MAX_HEALTH = 120
BASE_PLAYER_SPEED = 5
BASE_PLAYER_DAMAGE = 18
BASE_PLAYER_DEFENSE = 0

BACKGROUND = arcade.color.DARK_SLATE_GRAY
PANEL = arcade.color.DARK_BROWN
TEXT = arcade.color.WHITE
MUTED = arcade.color.LIGHT_GRAY
GOOD = arcade.color.AMAZON
BAD = arcade.color.RED_ORANGE


@dataclass
class Outfit:
    name: str
    description: str
    max_health_bonus: int = 0
    damage_bonus: int = 0
    speed_bonus: int = 0
    defense_bonus: int = 0
    sustainability: int = 0
    color: arcade.Color = arcade.color.WHITE


OUTFITS = [
    Outfit(
        "Thrifted Jacket",
        "Balanced gear from reuse. Small boost to everything.",
        max_health_bonus=12,
        damage_bonus=4,
        speed_bonus=1,
        defense_bonus=1,
        sustainability=3,
        color=arcade.color.SEA_GREEN,
    ),
    Outfit(
        "Upcycled Boots",
        "Fast and sustainable. Great for dodging and moving between floors.",
        max_health_bonus=4,
        damage_bonus=2,
        speed_bonus=3,
        defense_bonus=0,
        sustainability=4,
        color=arcade.color.DODGER_BLUE,
    ),
    Outfit(
        "Fast Fashion Suit",
        "Big immediate power, but the materials weaken you over time.",
        max_health_bonus=8,
        damage_bonus=10,
        speed_bonus=0,
        defense_bonus=0,
        sustainability=-4,
        color=arcade.color.ORANGE_RED,
    ),
]


class Entity:
    def __init__(self, x: float, y: float, width: float, height: float, color: arcade.Color):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.max_health = 1
        self.health = 1

    @property
    def center_x(self) -> float:
        return self.x

    @property
    def center_y(self) -> float:
        return self.y

    def rect(self) -> arcade.Rect:
        return arcade.Rect(
            self.x - self.width / 2,
            self.y - self.height / 2,
            self.width,
            self.height,
        )


class Player(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, 42, 56, arcade.color.AQUA)
        self.base_max_health = BASE_PLAYER_MAX_HEALTH
        self.base_damage = BASE_PLAYER_DAMAGE
        self.base_speed = BASE_PLAYER_SPEED
        self.defense = BASE_PLAYER_DEFENSE
        self.attack_timer = 0.0
        self.invuln_timer = 0.0
        self.money = 0
        self.floor = 1
        self.outfits: list[Outfit] = []
        self.max_health = self.base_max_health
        self.health = self.max_health

    @property
    def damage(self) -> int:
        return self.base_damage + sum(o.damage_bonus for o in self.outfits)

    @property
    def speed(self) -> int:
        return self.base_speed + sum(o.speed_bonus for o in self.outfits)

    @property
    def sustainability(self) -> int:
        return sum(o.sustainability for o in self.outfits)

    def refresh_stats(self) -> None:
        bonus_health = sum(o.max_health_bonus for o in self.outfits)
        self.max_health = self.base_max_health + bonus_health
        self.defense = BASE_PLAYER_DEFENSE + sum(o.defense_bonus for o in self.outfits)
        self.health = min(self.health, self.max_health)


class Enemy(Entity):
    def __init__(self, x: float, y: float, floor: int):
        size = 34 + floor * 2
        super().__init__(x, y, size, size, arcade.color.FIREBRICK)
        self.max_health = 40 + floor * 18
        self.health = self.max_health
        self.speed = 1.2 + floor * 0.25
        self.touch_damage = 8 + floor * 2


class Boss(Entity):
    def __init__(self):
        super().__init__(SCREEN_WIDTH / 2, SCREEN_HEIGHT - 180, 120, 120, arcade.color.PURPLE)
        self.max_health = 260
        self.health = self.max_health
        self.speed = 1.6
        self.touch_damage = 16


class GameView(arcade.View):
    def __init__(self) -> None:
        super().__init__()
        self.state = "intro"
        self.player = Player(160, 160)
        self.enemies: list[Enemy] = []
        self.boss = Boss()
        self.pressed_keys: set[int] = set()
        self.attack_flash = 0.0
        self.damage_flash = 0.0
        self.screen_shake = 0.0
        self.current_message = "Press ENTER to start the climb."
        self.reward_options: list[Outfit] = []
        self.reward_bounds: list[tuple[float, float, float, float]] = []

    def on_show_view(self) -> None:
        arcade.set_background_color(BACKGROUND)

    def spawn_floor(self) -> None:
        if self.player.floor >= 4:
            self.state = "boss"
            self.boss = Boss()
            self.boss.x = SCREEN_WIDTH / 2
            self.boss.y = SCREEN_HEIGHT - 160
            self.current_message = "The CEO appears."
            return
        self.enemies = [
            Enemy(random.randint(240, SCREEN_WIDTH - 80), random.randint(120, SCREEN_HEIGHT - 120), self.player.floor)
            for _ in range(2 + self.player.floor)
        ]
        self.state = "combat"

    def make_reward_options(self) -> list[Outfit]:
        pool = random.sample(OUTFITS, k=len(OUTFITS))
        return pool[:3]

    def apply_outfit(self, outfit: Outfit) -> None:
        self.player.outfits.append(outfit)
        self.player.refresh_stats()
        self.player.health = min(self.player.health + 12, self.player.max_health)
        self.player.money += max(1, outfit.sustainability + 2)
        self.player.floor += 1

    def current_outfit_options(self) -> list[Outfit]:
        return self.make_reward_options()

    def on_key_press(self, key: int, modifiers: int) -> None:
        self.pressed_keys.add(key)
        if self.state == "intro" and key == arcade.key.ENTER:
            self.player.floor = 1
            self.spawn_floor()
            self.current_message = "The climb begins. Clear the floor."
            return

        if self.state in {"game_over", "victory"} and key == arcade.key.R:
            self.__init__()
            return

        if self.state == "reward":
            choice = None
            if key in {arcade.key.ONE, arcade.key.KEY_1, arcade.key.NUM_1}:
                choice = 0
            elif key in {arcade.key.TWO, arcade.key.KEY_2, arcade.key.NUM_2}:
                choice = 1
            elif key in {arcade.key.THREE, arcade.key.KEY_3, arcade.key.NUM_3}:
                choice = 2
            if choice is not None and choice < len(self.reward_options):
                self.apply_outfit(self.reward_options[choice])
                self.spawn_floor()
            return

        if self.state in {"combat", "boss"} and key == arcade.key.SPACE:
            if self.player.attack_timer <= 0:
                self.attack()

    def on_key_release(self, key: int, modifiers: int) -> None:
        self.pressed_keys.discard(key)

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> None:
        if self.state != "reward" or button != arcade.MOUSE_BUTTON_LEFT:
            return
        for idx, bounds in enumerate(self.reward_bounds):
            left, right, bottom, top = bounds
            if left <= x <= right and bottom <= y <= top and idx < len(self.reward_options):
                self.apply_outfit(self.reward_options[idx])
                self.spawn_floor()
                return

    def attack(self) -> None:
        self.player.attack_timer = ATTACK_COOLDOWN
        self.attack_flash = 0.12
        targets = self.enemies if self.state == "combat" else [self.boss]
        hit = False
        for target in list(targets):
            if self.distance_to(target) <= ATTACK_RANGE:
                self.damage_target(target, self.player.damage)
                hit = True
        if hit:
            self.screen_shake = 0.08
        else:
            self.current_message = "No target in range. Move closer."

    def distance_to(self, target: Entity) -> float:
        return math.hypot(self.player.x - target.x, self.player.y - target.y)

    def damage_target(self, target: Entity, damage: int) -> None:
        target.health -= max(1, damage)
        target.x += random.randint(-10, 10)
        target.y += random.randint(-10, 10)

    def on_update(self, delta_time: float) -> None:
        if self.state in {"game_over", "victory"}:
            return

        if self.player.attack_timer > 0:
            self.player.attack_timer -= delta_time
        if self.player.invuln_timer > 0:
            self.player.invuln_timer -= delta_time
        if self.attack_flash > 0:
            self.attack_flash -= delta_time
        if self.damage_flash > 0:
            self.damage_flash -= delta_time
        if self.screen_shake > 0:
            self.screen_shake -= delta_time

        dx = dy = 0
        if arcade.key.LEFT in self.pressed_keys:
            dx -= 1
        if arcade.key.RIGHT in self.pressed_keys:
            dx += 1
        if arcade.key.UP in self.pressed_keys:
            dy += 1
        if arcade.key.DOWN in self.pressed_keys:
            dy -= 1

        magnitude = math.hypot(dx, dy)
        if magnitude:
            dx /= magnitude
            dy /= magnitude

        self.player.x = max(40, min(SCREEN_WIDTH - 40, self.player.x + dx * self.player.speed))
        self.player.y = max(40, min(SCREEN_HEIGHT - 40, self.player.y + dy * self.player.speed))

        if self.state == "combat":
            self.update_enemies()
            if not self.enemies:
                self.state = "reward"
                self.reward_options = self.current_outfit_options()
                self.current_message = "Floor cleared. Pick an outfit."
        elif self.state == "boss":
            self.update_boss()
            if self.boss.health <= 0:
                self.state = "victory"
                self.current_message = "The building falls. The planet gets a fighting chance."

    def update_enemies(self) -> None:
        for enemy in self.enemies[:]:
            self.move_toward(enemy, self.player, enemy.speed)
            if self.distance_between(enemy, self.player) < 32:
                self.hit_player(enemy.touch_damage)
            if enemy.health <= 0:
                self.enemies.remove(enemy)
                self.player.money += 5

    def update_boss(self) -> None:
        self.move_toward(self.boss, self.player, self.boss.speed)
        if self.distance_between(self.boss, self.player) < 48:
            self.hit_player(self.boss.touch_damage)

    def move_toward(self, mover: Entity, target: Entity, speed: float) -> None:
        dx = target.x - mover.x
        dy = target.y - mover.y
        dist = math.hypot(dx, dy) or 1
        mover.x += dx / dist * speed
        mover.y += dy / dist * speed
        mover.x = max(40, min(SCREEN_WIDTH - 40, mover.x))
        mover.y = max(40, min(SCREEN_HEIGHT - 40, mover.y))

    def distance_between(self, a: Entity, b: Entity) -> float:
        return math.hypot(a.x - b.x, a.y - b.y)

    def hit_player(self, incoming: int) -> None:
        if self.player.invuln_timer > 0:
            return
        damage = max(1, incoming - self.player.defense)
        self.player.health -= damage
        self.player.invuln_timer = 0.6
        self.damage_flash = 0.18
        self.current_message = f"You took {damage} damage."
        if self.player.health <= 0:
            self.state = "game_over"
            self.current_message = "The movement stalled. Press R to retry."

    def on_draw(self) -> None:
        self.clear()
        shake_x = random.randint(-2, 2) if self.screen_shake > 0 else 0
        shake_y = random.randint(-2, 2) if self.screen_shake > 0 else 0

        arcade.draw_lbwh_rectangle_filled(0 + shake_x, 0 + shake_y, SCREEN_WIDTH, SCREEN_HEIGHT, BACKGROUND)
        self.draw_background()
        self.draw_building(shake_x, shake_y)
        self.draw_entities(shake_x, shake_y)
        self.draw_ui()
        self.draw_messages()

        if self.state == "intro":
            self.draw_center_panel("Hunter & Ollin", "Use arrow keys to move. Press SPACE to attack. Press ENTER to start.")
        elif self.state == "reward":
            self.draw_reward_menu()
        elif self.state == "game_over":
            self.draw_center_panel("Game Over", "Press R to restart.")
        elif self.state == "victory":
            self.draw_center_panel("Victory", "You defeated the CEO. Press R to play again.")

    def draw_building(self, shake_x: int, shake_y: int) -> None:
        arcade.draw_lrbt_rectangle_filled(180 + shake_x, SCREEN_WIDTH - 180 + shake_x, 40 + shake_y, SCREEN_HEIGHT - 40 + shake_y, arcade.color.DARK_BROWN)
        arcade.draw_lrbt_rectangle_outline(180 + shake_x, SCREEN_WIDTH - 180 + shake_x, 40 + shake_y, SCREEN_HEIGHT - 40 + shake_y, arcade.color.BLACK_OLIVE, 4)
        for floor_y in range(110, SCREEN_HEIGHT - 50, 110):
            arcade.draw_line(180 + shake_x, floor_y + shake_y, SCREEN_WIDTH - 180 + shake_x, floor_y + shake_y, arcade.color.BLACK_OLIVE, 3)
        for window_y in range(80, SCREEN_HEIGHT - 80, 110):
            for window_x in range(230, SCREEN_WIDTH - 220, 150):
                lit = (window_x + window_y) % 3 != 0
                color = arcade.color.GOLD if lit else arcade.color.DARK_SLATE_GRAY
                arcade.draw_lbwh_rectangle_filled(window_x - 13 + shake_x, window_y - 17 + shake_y, 26, 34, color)
                arcade.draw_lbwh_rectangle_outline(window_x - 13 + shake_x, window_y - 17 + shake_y, 26, 34, arcade.color.BLACK, 1)

    def draw_background(self) -> None:
        for i, alpha in enumerate((22, 18, 14, 10)):
            y = 40 + i * 150
            arcade.draw_arc_filled(SCREEN_WIDTH / 2, y, SCREEN_WIDTH + 260, 180, arcade.color.DARK_SLATE_GRAY, 0, 180)
        arcade.draw_circle_filled(110, SCREEN_HEIGHT - 110, 48, arcade.color.DARK_GOLDENROD)
        arcade.draw_circle_filled(SCREEN_WIDTH - 110, SCREEN_HEIGHT - 140, 26, arcade.color.LIGHT_GRAY)
        for x in range(80, SCREEN_WIDTH, 140):
            arcade.draw_line(x, 0, x + 60, 0, arcade.color.BLACK_OLIVE, 4)

    def draw_entities(self, shake_x: int, shake_y: int) -> None:
        self.draw_entity(self.player, shake_x, shake_y, arcade.color.AQUA)
        for enemy in self.enemies:
            self.draw_entity(enemy, shake_x, shake_y, enemy.color)
        if self.state in {"boss", "victory"}:
            self.draw_entity(self.boss, shake_x, shake_y, self.boss.color)
        if self.attack_flash > 0:
            arcade.draw_circle_outline(self.player.x + shake_x, self.player.y + shake_y, ATTACK_RANGE, arcade.color.YELLOW, 3)

    def draw_entity(self, entity: Entity, shake_x: int, shake_y: int, color: arcade.Color) -> None:
        arcade.draw_lbwh_rectangle_filled(
            entity.x - entity.width / 2 + shake_x,
            entity.y - entity.height / 2 + shake_y,
            entity.width,
            entity.height,
            color,
        )
        health_ratio = max(0, entity.health) / entity.max_health
        arcade.draw_lbwh_rectangle_filled(
            entity.x - entity.width / 2 + shake_x,
            entity.y + entity.height / 2 + 10 + shake_y,
            entity.width,
            6,
            arcade.color.DARK_RED,
        )
        arcade.draw_lbwh_rectangle_filled(
            entity.x - entity.width / 2 + shake_x,
            entity.y + entity.height / 2 + 10 + shake_y,
            entity.width * health_ratio,
            6,
            arcade.color.LIME_GREEN,
        )

    def draw_ui(self) -> None:
        arcade.draw_lrbt_rectangle_filled(18, 420, SCREEN_HEIGHT - 150, SCREEN_HEIGHT - 18, PANEL)
        arcade.draw_text(f"Health: {self.player.health}/{self.player.max_health}", 30, SCREEN_HEIGHT - 56, TEXT, 16)
        arcade.draw_text(f"Money: {self.player.money}", 30, SCREEN_HEIGHT - 82, TEXT, 16)
        arcade.draw_text(f"Floor: {self.player.floor}", 30, SCREEN_HEIGHT - 108, TEXT, 16)
        arcade.draw_text(f"Damage: {self.player.damage}  Speed: {self.player.speed}  Sustainability: {self.player.sustainability}", 30, SCREEN_HEIGHT - 134, MUTED, 12)

        arcade.draw_lrbt_rectangle_filled(SCREEN_WIDTH - 250, SCREEN_WIDTH - 18, SCREEN_HEIGHT - 150, SCREEN_HEIGHT - 18, PANEL)
        arcade.draw_text("Objectives", SCREEN_WIDTH - 232, SCREEN_HEIGHT - 56, TEXT, 16)
        if self.state == "boss":
            objective = "Defeat the CEO"
        elif self.state == "reward":
            objective = "Choose your next outfit"
        else:
            objective = "Clear the floor"
        arcade.draw_text(objective, SCREEN_WIDTH - 232, SCREEN_HEIGHT - 82, MUTED, 14)
        arcade.draw_text("Move: arrows", SCREEN_WIDTH - 232, SCREEN_HEIGHT - 108, MUTED, 12)
        arcade.draw_text("Attack: space", SCREEN_WIDTH - 232, SCREEN_HEIGHT - 126, MUTED, 12)

    def draw_messages(self) -> None:
        arcade.draw_text(self.current_message, SCREEN_WIDTH / 2, 24, arcade.color.GOLD, 14, anchor_x="center")

    def draw_center_panel(self, title: str, subtitle: str) -> None:
        arcade.draw_lbwh_rectangle_filled(SCREEN_WIDTH / 2 - 280, SCREEN_HEIGHT / 2 - 110, 560, 220, arcade.color.BLACK_OLIVE)
        arcade.draw_lbwh_rectangle_outline(SCREEN_WIDTH / 2 - 280, SCREEN_HEIGHT / 2 - 110, 560, 220, arcade.color.WHITE, 3)
        arcade.draw_text(title, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 40, TEXT, 34, anchor_x="center")
        arcade.draw_text(subtitle, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 12, MUTED, 14, anchor_x="center")

    def draw_reward_menu(self) -> None:
        panel_left = SCREEN_WIDTH / 2 - 380
        panel_bottom = SCREEN_HEIGHT / 2 - 170
        arcade.draw_lbwh_rectangle_filled(panel_left, panel_bottom, 760, 340, arcade.color.DARK_BLUE_GRAY)
        arcade.draw_lbwh_rectangle_outline(panel_left, panel_bottom, 760, 340, arcade.color.WHITE, 3)
        arcade.draw_text("Pick one outfit", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 128, TEXT, 30, anchor_x="center")
        arcade.draw_text("Click a card or press 1, 2, or 3", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 94, MUTED, 14, anchor_x="center")
        self.reward_bounds = []
        for idx, outfit in enumerate(self.reward_options):
            y = SCREEN_HEIGHT / 2 + 30 - idx * 92
            left = SCREEN_WIDTH / 2 - 330
            bottom = y - 36
            right = SCREEN_WIDTH / 2 + 330
            top = y + 36
            self.reward_bounds.append((left, right, bottom, top))
            arcade.draw_lbwh_rectangle_filled(left + 4, bottom - 4, 660, 72, arcade.color.BLACK)
            arcade.draw_lbwh_rectangle_filled(left, bottom, 660, 72, outfit.color)
            arcade.draw_lbwh_rectangle_outline(left, bottom, 660, 72, arcade.color.WHITE, 3)
            arcade.draw_circle_filled(left + 42, y, 20, arcade.color.WHITE)
            arcade.draw_text(str(idx + 1), left + 42, y - 8, arcade.color.BLACK, 18, anchor_x="center")
            arcade.draw_text(outfit.name, left + 86, y + 14, arcade.color.BLACK, 18)
            arcade.draw_text(outfit.description, left + 86, y - 10, arcade.color.BLACK, 11)
            stats = f"HP +{outfit.max_health_bonus}  DMG +{outfit.damage_bonus}  SPD +{outfit.speed_bonus}  SUS {outfit.sustainability:+d}"
            arcade.draw_text(stats, left + 86, y - 28, arcade.color.BLACK, 10)


def main() -> None:
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    view = GameView()
    window.show_view(view)
    arcade.run()


if __name__ == "__main__":
    main()
