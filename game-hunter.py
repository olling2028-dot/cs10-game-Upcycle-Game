"""Hunter & Ollin serious game MVP.

This version turns the design doc into a small playable vertical slice:
- Move through the build
- Fight enemies with basic attacks
- Pick outfits after each floor
- Balance power vs sustainability tradeoffs
- Defeat the CEO boss, shop, and keep climbing forever
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
ATTACK_COOLDOWN = 0.16
ATTACK_RANGE = 70
ATTACK_DAMAGE = 18
ATTACK_BOX_LENGTH = 84
ATTACK_BOX_WIDTH = 56
PUNCH_ANIMATION_TIME = 0.1
SPECIAL_ATTACK_COOLDOWN = 0.58
LUNGE_DASH_DISTANCE = 88
LUNGE_DASH_TIME = 0.14
BASE_PLAYER_MAX_HEALTH = 120
BASE_PLAYER_SPEED = 5
BASE_PLAYER_DAMAGE = 18
BASE_PLAYER_DEFENSE = 0
MALAISE_MAX = 100.0
MALAISE_GAIN_RATE = 1.0
MALAISE_RECOVERY_RATE = 0.28
MALAISE_DAMAGE_INTERVAL = 1.6
MALAISE_TICK_THRESHOLD = 55.0
MALAISE_TICK_DAMAGE = 2
MALAISE_KILL_RECOVERY = 10.0
MALAISE_PASSIVE_RECOVERY = 0.18

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

    def rect(self, padding_x: float = 0.0, padding_y: float = 0.0) -> tuple[float, float, float, float]:
        left = self.x - self.width / 2 + padding_x
        right = self.x + self.width / 2 - padding_x
        bottom = self.y - self.height / 2 + padding_y
        top = self.y + self.height / 2 - padding_y
        return left, right, bottom, top


class Player(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, 42, 56, arcade.color.AQUA)
        self.base_max_health = BASE_PLAYER_MAX_HEALTH
        self.base_damage = BASE_PLAYER_DAMAGE
        self.base_speed = BASE_PLAYER_SPEED
        self.defense = BASE_PLAYER_DEFENSE
        self.attack_timer = 0.0
        self.invuln_timer = 0.0
        self.facing_x = 1.0
        self.facing_y = 0.0
        self.microplastics = 0.0
        self.microplastics_tick = 0.0
        self.money = 0
        self.floor = 1
        self.outfits: list[Outfit] = []
        self.unlocked_attacks: set[str] = {"basic"}
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

    @property
    def microplastics_stage(self) -> int:
        return min(3, int(self.microplastics // 25))

    @property
    def effective_damage(self) -> int:
        return max(1, self.damage - self.microplastics_stage * 2)

    @property
    def effective_speed(self) -> int:
        return max(2, self.speed - self.microplastics_stage)

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
        self.punch_timer = 0.0
        self.special_attack_timer = 0.0
        self.special_attack_effect = ""
        self.special_attack_effect_timer = 0.0
        self.lunge_dash_timer = 0.0
        self.lunge_dash_dx = 0.0
        self.lunge_dash_dy = 0.0
        self.damage_flash = 0.0
        self.screen_shake = 0.0
        self.current_message = "Press ENTER to start the climb."
        self.reward_options: list[Outfit] = []
        self.reward_bounds: list[tuple[float, float, float, float]] = []
        self.shop_options: list[tuple[str, str, int, str]] = []
        self.shop_bounds: list[tuple[float, float, float, float]] = []
        self.shop_message = "Spend money with 1-4, then press SPACE."
        self.shop_open_timer = 0.0

    def on_show_view(self) -> None:
        arcade.set_background_color(BACKGROUND)

    def spawn_floor(self) -> None:
        if self.player.floor % 4 == 0:
            self.state = "boss"
            self.boss = Boss()
            self.boss.x = SCREEN_WIDTH / 2
            self.boss.y = SCREEN_HEIGHT - 160
            self.current_message = "The CEO appears."
            return
        self.enemies = []
        for _ in range(2 + self.player.floor):
            x, y = self.random_enemy_spawn_point()
            self.enemies.append(Enemy(x, y, self.player.floor))
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

    def open_shop(self) -> None:
        self.state = "shop"
        self.refresh_shop_options()
        self.current_message = self.shop_message
        self.pressed_keys.clear()
        self.shop_open_timer = 0.0

    def random_enemy_spawn_point(self) -> tuple[float, float]:
        min_distance = 180
        for _ in range(40):
            x = random.randint(80, SCREEN_WIDTH - 80)
            y = random.randint(80, SCREEN_HEIGHT - 80)
            if math.hypot(x - self.player.x, y - self.player.y) >= min_distance:
                return x, y
        angle = random.random() * math.tau
        return (
            max(80, min(SCREEN_WIDTH - 80, self.player.x + math.cos(angle) * min_distance)),
            max(80, min(SCREEN_HEIGHT - 80, self.player.y + math.sin(angle) * min_distance)),
        )

    def on_key_press(self, key: int, modifiers: int) -> None:
        self.pressed_keys.add(key)
        if self.state == "intro" and key == arcade.key.ENTER:
            self.player.floor = 1
            self.spawn_floor()
            self.current_message = "The climb begins. Clear the floor."
            return

        if self.state == "game_over" and key == arcade.key.R:
            self.__init__()
            return

        if self.state == "shop":
            if key in {arcade.key.KEY_1, arcade.key.NUM_1}:
                self.buy_shop_item(self.shop_options[0][0])
            elif key in {arcade.key.KEY_2, arcade.key.NUM_2}:
                self.buy_shop_item(self.shop_options[1][0])
            elif key in {arcade.key.KEY_3, arcade.key.NUM_3}:
                self.buy_shop_item(self.shop_options[2][0])
            elif key in {arcade.key.KEY_4, arcade.key.NUM_4}:
                self.buy_shop_item(self.shop_options[3][0])
            elif key in {arcade.key.SPACE, arcade.key.ENTER, arcade.key.RETURN}:
                if self.shop_open_timer >= 3.0:
                    self.advance_after_shop()
                else:
                    remaining = max(0.0, 3.0 - self.shop_open_timer)
                    self.current_message = f"Shop just opened. Wait {remaining:.1f}s to leave."
                self.pressed_keys.discard(arcade.key.SPACE)
            return

        if self.state == "reward":
            choice = None
            if key in {arcade.key.KEY_1, arcade.key.NUM_1}:
                choice = 0
            elif key in {arcade.key.KEY_2, arcade.key.NUM_2}:
                choice = 1
            elif key in {arcade.key.KEY_3, arcade.key.NUM_3}:
                choice = 2
            if choice is not None and choice < len(self.reward_options):
                self.apply_outfit(self.reward_options[choice])
                self.spawn_floor()
            return

        if self.state in {"combat", "boss"} and key == arcade.key.SPACE:
            if self.player.attack_timer <= 0:
                self.attack()
        if self.state in {"combat", "boss"} and key in {arcade.key.Q, arcade.key.E}:
            self.special_attack(key)

    def on_key_release(self, key: int, modifiers: int) -> None:
        self.pressed_keys.discard(key)

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> None:
        if self.state != "reward" or button != arcade.MOUSE_BUTTON_LEFT:
            if self.state == "shop" and button == arcade.MOUSE_BUTTON_LEFT:
                for idx, bounds in enumerate(self.shop_bounds):
                    left, right, bottom, top = bounds
                    if left <= x <= right and bottom <= y <= top:
                        self.buy_shop_item(self.shop_options[idx][0])
                        return
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
        self.punch_timer = PUNCH_ANIMATION_TIME
        targets = self.enemies if self.state == "combat" else [self.boss]
        hit = False
        attack_rect = self.attack_rect()
        for target in list(targets):
            if self.rects_intersect(attack_rect, self.entity_hitbox(target, 0), padding=4):
                self.damage_target(target, self.player.effective_damage)
                hit = True
        if hit:
            self.screen_shake = 0.08
        else:
            self.current_message = "No target in range. Move closer."

    def special_attack(self, key: int) -> None:
        if self.special_attack_timer > 0:
            return
        if key == arcade.key.Q and "sweep" in self.player.unlocked_attacks:
            self.special_attack_timer = SPECIAL_ATTACK_COOLDOWN
            self.special_attack_effect = "sweep"
            self.special_attack_effect_timer = 0.24
            self.current_message = "Sweep attack!"
            targets = self.enemies if self.state == "combat" else [self.boss]
            hit = False
            sweep_rect = (
                self.player.x - 110,
                self.player.x + 110,
                self.player.y - 86,
                self.player.y + 86,
            )
            for target in list(targets):
                if self.rects_intersect(sweep_rect, self.entity_hitbox(target, 4), padding=6):
                    self.damage_target(target, self.player.effective_damage + 6)
                    hit = True
            if hit:
                self.screen_shake = 0.1
            return
        if key == arcade.key.E and "lunge" in self.player.unlocked_attacks:
            self.special_attack_timer = SPECIAL_ATTACK_COOLDOWN
            self.special_attack_effect = "lunge"
            self.special_attack_effect_timer = 0.26
            self.current_message = "Lunge strike!"
            facing_x = self.player.facing_x
            facing_y = self.player.facing_y
            if facing_x == 0 and facing_y == 0:
                facing_x = 1.0
            facing_length = math.hypot(facing_x, facing_y) or 1.0
            self.lunge_dash_dx = facing_x / facing_length
            self.lunge_dash_dy = facing_y / facing_length
            self.lunge_dash_timer = LUNGE_DASH_TIME
            self.player.x += self.lunge_dash_dx * LUNGE_DASH_DISTANCE * 0.35
            self.player.y += self.lunge_dash_dy * LUNGE_DASH_DISTANCE * 0.35
            targets = self.enemies if self.state == "combat" else [self.boss]
            hit = False
            for target in list(targets):
                line_dx = target.x - self.player.x
                line_dy = target.y - self.player.y
                forward = line_dx * self.lunge_dash_dx + line_dy * self.lunge_dash_dy
                if 0 <= forward <= 150 and abs(line_dx * self.lunge_dash_dy - line_dy * self.lunge_dash_dx) <= 58:
                    self.damage_target(target, self.player.effective_damage + 10)
                    hit = True
            if hit:
                self.screen_shake = 0.1

    def attack_rect(self) -> tuple[float, float, float, float]:
        length = ATTACK_BOX_LENGTH
        width = ATTACK_BOX_WIDTH
        offset = self.player.width / 2 + length / 2 - 2
        if self.player.facing_x > 0:
            return (
                self.player.x + offset - length / 2,
                self.player.x + offset + length / 2,
                self.player.y - width / 2,
                self.player.y + width / 2,
            )
        if self.player.facing_x < 0:
            return (
                self.player.x - offset - length / 2,
                self.player.x - offset + length / 2,
                self.player.y - width / 2,
                self.player.y + width / 2,
            )
        offset = self.player.height / 2 + length / 2 - 2
        if self.player.facing_y >= 0:
            return (
                self.player.x - width / 2,
                self.player.x + width / 2,
                self.player.y + offset - length / 2,
                self.player.y + offset + length / 2,
            )
        return (
            self.player.x - width / 2,
            self.player.x + width / 2,
            self.player.y - offset - length / 2,
            self.player.y - offset + length / 2,
        )

    def entity_hitbox(self, entity: Entity, padding: float = 0.0) -> tuple[float, float, float, float]:
        return entity.rect(padding, padding)

    @staticmethod
    def rects_intersect(
        a: tuple[float, float, float, float],
        b: tuple[float, float, float, float],
        padding: float = 0.0,
    ) -> bool:
        a_left, a_right, a_bottom, a_top = a
        b_left, b_right, b_bottom, b_top = b
        a_left -= padding
        a_right += padding
        a_bottom -= padding
        a_top += padding
        b_left -= padding
        b_right += padding
        b_bottom -= padding
        b_top += padding
        return not (
            a_right <= b_left
            or b_right <= a_left
            or a_top <= b_bottom
            or b_top <= a_bottom
        )

    def damage_target(self, target: Entity, damage: int) -> None:
        target.health -= max(1, damage)
        target.x = max(40, min(SCREEN_WIDTH - 40, target.x))
        target.y = max(40, min(SCREEN_HEIGHT - 40, target.y))

    def on_update(self, delta_time: float) -> None:
        if self.state == "game_over":
            return

        if self.player.attack_timer > 0:
            self.player.attack_timer -= delta_time
        if self.special_attack_timer > 0:
            self.special_attack_timer -= delta_time
        if self.special_attack_effect_timer > 0:
            self.special_attack_effect_timer -= delta_time
            if self.special_attack_effect_timer <= 0:
                self.special_attack_effect = ""
        if self.lunge_dash_timer > 0:
            dash_step = LUNGE_DASH_DISTANCE / LUNGE_DASH_TIME * delta_time
            self.player.x += self.lunge_dash_dx * dash_step
            self.player.y += self.lunge_dash_dy * dash_step
            self.player.x = max(40, min(SCREEN_WIDTH - 40, self.player.x))
            self.player.y = max(40, min(SCREEN_HEIGHT - 40, self.player.y))
            self.lunge_dash_timer -= delta_time
        if self.player.invuln_timer > 0:
            self.player.invuln_timer -= delta_time
        if self.attack_flash > 0:
            self.attack_flash -= delta_time
        if self.punch_timer > 0:
            self.punch_timer -= delta_time
        if self.damage_flash > 0:
            self.damage_flash -= delta_time
        if self.screen_shake > 0:
            self.screen_shake -= delta_time
        if self.state == "shop":
            self.shop_open_timer += delta_time
        self.update_microplastics(delta_time)

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
            if abs(dx) >= abs(dy):
                self.player.facing_x = 1.0 if dx >= 0 else -1.0
                self.player.facing_y = 0.0
            else:
                self.player.facing_x = 0.0
                self.player.facing_y = 1.0 if dy >= 0 else -1.0

        self.player.x = max(40, min(SCREEN_WIDTH - 40, self.player.x + dx * self.player.effective_speed))
        self.player.y = max(40, min(SCREEN_HEIGHT - 40, self.player.y + dy * self.player.effective_speed))

        if self.state == "combat":
            self.update_enemies()
            if not self.enemies:
                self.state = "reward"
                self.reward_options = self.current_outfit_options()
                self.current_message = "Floor cleared. Pick an outfit."
        elif self.state == "boss":
            self.update_boss()
            if self.boss.health <= 0:
                self.open_shop()

    def update_microplastics(self, delta_time: float) -> None:
        if self.state == "shop":
            self.player.microplastics_tick = 0.0
            return
        sustainability = self.player.sustainability
        if sustainability < 0:
            self.player.microplastics += ((-sustainability) ** 0.85) * MALAISE_GAIN_RATE * 0.75 * delta_time
        elif sustainability > 0:
            self.player.microplastics -= sustainability * MALAISE_RECOVERY_RATE * 1.5 * delta_time
        self.player.microplastics -= MALAISE_PASSIVE_RECOVERY * delta_time
        self.player.microplastics = max(0.0, min(MALAISE_MAX, self.player.microplastics))

        if self.player.microplastics >= MALAISE_TICK_THRESHOLD:
            self.player.microplastics_tick += delta_time
            if self.player.microplastics_tick >= MALAISE_DAMAGE_INTERVAL:
                self.player.microplastics_tick = 0.0
                self.hit_player(MALAISE_TICK_DAMAGE)
        else:
            self.player.microplastics_tick = 0.0

    def update_enemies(self) -> None:
        for enemy in self.enemies[:]:
            self.move_toward(enemy, self.player, enemy.speed)
            if self.rects_intersect(self.entity_hitbox(enemy, 2), self.entity_hitbox(self.player, 3)):
                self.hit_player(enemy.touch_damage)
            if enemy.health <= 0:
                self.enemies.remove(enemy)
                self.player.money += 5
                self.player.microplastics = max(0.0, self.player.microplastics - MALAISE_KILL_RECOVERY)
                self.current_message = "Enemy down. Microplastics dropped."

    def update_boss(self) -> None:
        self.move_toward(self.boss, self.player, self.boss.speed)
        if self.rects_intersect(self.entity_hitbox(self.boss, 4), self.entity_hitbox(self.player, 3)):
            self.hit_player(self.boss.touch_damage)

    def buy_shop_item(self, item: str) -> None:
        costs = {"heal": 8, "damage": 12, "speed": 12, "defense": 12, "unlock_sweep": 18, "unlock_lunge": 24}
        if self.player.money < costs[item]:
            self.current_message = "Not enough money."
            return
        self.player.money -= costs[item]
        if item == "heal":
            self.player.health = min(self.player.max_health, self.player.health + 30)
            self.current_message = "Recovered some health."
        elif item == "damage":
            self.player.base_damage += 3
            self.current_message = "Damage upgraded."
        elif item == "speed":
            self.player.base_speed += 1
            self.current_message = "Speed upgraded."
        elif item == "defense":
            self.player.defense += 1
            self.current_message = "Defense upgraded."
        elif item == "unlock_sweep":
            self.player.unlocked_attacks.add("sweep")
            self.current_message = "Unlocked Sweep Attack (Q)."
        elif item == "unlock_lunge":
            self.player.unlocked_attacks.add("lunge")
            self.current_message = "Unlocked Lunge Strike (E)."
        self.player.money = max(0, self.player.money)

    def refresh_shop_options(self) -> None:
        options: list[tuple[str, str, int, str]] = [
            ("heal", "Repair kit", 8, "common"),
            ("damage", "Tool upgrade", 12, "common"),
        ]
        third = ("speed", "Quickstep boots", 12, "common")
        fourth = ("defense", "Reinforced lining", 12, "common")
        if self.player.floor >= 3 and "sweep" not in self.player.unlocked_attacks:
            third = ("unlock_sweep", "Sweep emitter", 18, "rare")
        elif self.player.floor >= 7 and random.random() < 0.5:
            third = ("damage", "Prototype edge", 20, "rare")
        if self.player.floor >= 5 and "lunge" not in self.player.unlocked_attacks:
            fourth = ("unlock_lunge", "Lunge drive", 24, "rare")
        elif self.player.floor >= 9 and random.random() < 0.4:
            fourth = ("speed", "Slipstream weave", 20, "rare")
        options.extend([third, fourth])
        self.shop_options = options

    def advance_after_shop(self) -> None:
        self.player.floor += 1
        self.spawn_floor()
        self.current_message = "Next floor."

    def move_toward(self, mover: Entity, target: Entity, speed: float) -> None:
        dx = target.x - mover.x
        dy = target.y - mover.y
        dist = math.hypot(dx, dy) or 1
        mover.x += dx / dist * speed
        mover.y += dy / dist * speed
        mover.x = max(40, min(SCREEN_WIDTH - 40, mover.x))
        mover.y = max(40, min(SCREEN_HEIGHT - 40, mover.y))

    def hit_player(self, incoming: int) -> None:
        if self.player.invuln_timer > 0:
            return
        malaise_penalty = int(self.player.microplastics // 25)
        damage = max(1, incoming - self.player.defense + malaise_penalty)
        self.player.health -= damage
        self.player.microplastics = min(MALAISE_MAX, self.player.microplastics + damage * 1.7)
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
        elif self.state == "shop":
            self.draw_center_panel("Shop", "Spend money with 1-4, then press SPACE.")
            self.draw_shop_menu()

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
        if self.state == "boss":
            self.draw_entity(self.boss, shake_x, shake_y, self.boss.color)
        if self.punch_timer > 0:
            self.draw_punch(shake_x, shake_y)
        if self.special_attack_effect_timer > 0:
            self.draw_special_attack_effect(shake_x, shake_y)

    def draw_punch(self, shake_x: int, shake_y: int) -> None:
        progress = 1.0 - max(0.0, self.punch_timer) / PUNCH_ANIMATION_TIME
        reach = 18 + progress * 38
        if self.player.facing_x > 0:
            start_x = self.player.x + self.player.width / 2 + shake_x - 2
            start_y = self.player.y + shake_y + 4
            punch_x = self.player.x + self.player.width / 2 + reach + shake_x
            punch_y = self.player.y + shake_y + 2
        elif self.player.facing_x < 0:
            start_x = self.player.x - self.player.width / 2 + shake_x + 2
            start_y = self.player.y + shake_y + 4
            punch_x = self.player.x - self.player.width / 2 - reach + shake_x
            punch_y = self.player.y + shake_y + 2
        elif self.player.facing_y >= 0:
            start_x = self.player.x + shake_x + 2
            start_y = self.player.y + self.player.height / 2 + shake_y - 2
            punch_x = self.player.x + shake_x + 2
            punch_y = self.player.y + self.player.height / 2 + reach + shake_y
        else:
            start_x = self.player.x + shake_x + 2
            start_y = self.player.y - self.player.height / 2 + shake_y + 2
            punch_x = self.player.x + shake_x + 2
            punch_y = self.player.y - self.player.height / 2 - reach + shake_y
        arcade.draw_line(start_x, start_y, punch_x, punch_y, arcade.color.BEIGE, 8)
        arcade.draw_circle_filled(punch_x, punch_y, 10, arcade.color.WHITE_SMOKE)
        arcade.draw_circle_outline(punch_x, punch_y, 10, arcade.color.BLACK, 2)

    def draw_special_attack_effect(self, shake_x: int, shake_y: int) -> None:
        if self.special_attack_effect == "sweep":
            arcade.draw_arc_outline(
                self.player.x + shake_x,
                self.player.y + shake_y,
                170,
                170,
                arcade.color.MEDIUM_AQUAMARINE,
                20,
                160,
                340,
                8,
            )
            arcade.draw_circle_outline(self.player.x + shake_x, self.player.y + shake_y, 58, arcade.color.WHITE, 3)
        elif self.special_attack_effect == "lunge":
            facing_x = self.player.facing_x
            facing_y = self.player.facing_y
            if facing_x == 0 and facing_y == 0:
                facing_x = 1.0
            end_x = self.player.x + facing_x * 92 + shake_x
            end_y = self.player.y + facing_y * 92 + shake_y
            arcade.draw_line(
                self.player.x + shake_x,
                self.player.y + shake_y,
                end_x,
                end_y,
                arcade.color.YELLOW_ORANGE,
                10,
            )
            arcade.draw_triangle_filled(
                end_x,
                end_y,
                end_x - facing_y * 14 - facing_x * 8,
                end_y + facing_x * 14 - facing_y * 8,
                end_x + facing_y * 14 - facing_x * 8,
                end_y - facing_x * 14 - facing_y * 8,
                arcade.color.WHITE,
            )

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
        arcade.draw_text(
            f"Damage: {self.player.effective_damage}  Speed: {self.player.effective_speed}  Sustainability: {self.player.sustainability}",
            30,
            SCREEN_HEIGHT - 134,
            MUTED,
            12,
        )
        stage = self.player.microplastics_stage
        stage_text = ["Clean", "Dirty", "Toxic", "Critical"][stage]
        arcade.draw_text(
            f"Microplastics: {int(self.player.microplastics)}/100  Stage: {stage_text}",
            30,
            SCREEN_HEIGHT - 152,
            MUTED,
            12,
        )
        bar_left = 30
        bar_bottom = SCREEN_HEIGHT - 176
        bar_width = 320
        bar_height = 16
        fill_width = bar_width * (self.player.microplastics / MALAISE_MAX)
        if self.player.microplastics < 40:
            bar_color = arcade.color.AMAZON
        elif self.player.microplastics < 70:
            bar_color = arcade.color.GOLD
        else:
            bar_color = arcade.color.RED_ORANGE
        arcade.draw_lbwh_rectangle_outline(bar_left, bar_bottom, bar_width, bar_height, arcade.color.WHITE, 1)
        arcade.draw_lbwh_rectangle_filled(bar_left, bar_bottom, fill_width, bar_height, bar_color)
        for tick in (25, 50, 75):
            x = bar_left + bar_width * (tick / MALAISE_MAX)
            arcade.draw_line(x, bar_bottom, x, bar_bottom + bar_height, arcade.color.WHITE, 1)
        arcade.draw_text("Lower is better", bar_left + 2, bar_bottom - 16, MUTED, 10)

        arcade.draw_lrbt_rectangle_filled(SCREEN_WIDTH - 250, SCREEN_WIDTH - 18, SCREEN_HEIGHT - 150, SCREEN_HEIGHT - 18, PANEL)
        arcade.draw_text("Objectives", SCREEN_WIDTH - 232, SCREEN_HEIGHT - 56, TEXT, 16)
        if self.state == "boss":
            objective = "Defeat the CEO"
        elif self.state == "shop":
            objective = "Spend money before the next floor"
        elif self.state == "reward":
            objective = "Choose your next outfit"
        else:
            objective = "Clear the floor"
        arcade.draw_text(objective, SCREEN_WIDTH - 232, SCREEN_HEIGHT - 82, MUTED, 14)
        arcade.draw_text("Move: arrows", SCREEN_WIDTH - 232, SCREEN_HEIGHT - 108, MUTED, 12)
        arcade.draw_text("Attack: space", SCREEN_WIDTH - 232, SCREEN_HEIGHT - 126, MUTED, 12)
        if "sweep" in self.player.unlocked_attacks:
            arcade.draw_text("Sweep: Q", SCREEN_WIDTH - 232, SCREEN_HEIGHT - 144, MUTED, 12)
        if "lunge" in self.player.unlocked_attacks:
            arcade.draw_text("Lunge: E", SCREEN_WIDTH - 232, SCREEN_HEIGHT - 162, MUTED, 12)
        if self.state == "shop":
            arcade.draw_text("1-4 or click items", SCREEN_WIDTH - 232, SCREEN_HEIGHT - 154, MUTED, 12)
            arcade.draw_text("SPACE or ENTER to continue", SCREEN_WIDTH - 232, SCREEN_HEIGHT - 172, MUTED, 12)
            arcade.draw_text("Buy what you can, then leave", SCREEN_WIDTH - 232, SCREEN_HEIGHT - 226, MUTED, 12)

    def draw_messages(self) -> None:
        arcade.draw_text(self.current_message, SCREEN_WIDTH / 2, 24, arcade.color.GOLD, 14, anchor_x="center")

    def draw_center_panel(self, title: str, subtitle: str) -> None:
        arcade.draw_lbwh_rectangle_filled(SCREEN_WIDTH / 2 - 280, SCREEN_HEIGHT / 2 - 110, 560, 220, arcade.color.BLACK_OLIVE)
        arcade.draw_lbwh_rectangle_outline(SCREEN_WIDTH / 2 - 280, SCREEN_HEIGHT / 2 - 110, 560, 220, arcade.color.WHITE, 3)
        arcade.draw_text(title, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 40, TEXT, 34, anchor_x="center")
        arcade.draw_text(subtitle, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 12, MUTED, 14, anchor_x="center")

    def draw_shop_menu(self) -> None:
        panel_left = SCREEN_WIDTH / 2 - 380
        panel_bottom = SCREEN_HEIGHT / 2 - 170
        arcade.draw_lbwh_rectangle_filled(panel_left, panel_bottom, 760, 340, arcade.color.DARK_BLUE_GRAY)
        arcade.draw_lbwh_rectangle_outline(panel_left, panel_bottom, 760, 340, arcade.color.WHITE, 3)
        arcade.draw_text("Shop", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 128, TEXT, 30, anchor_x="center")
        arcade.draw_text("Buy upgrades with money, or press SPACE when finished", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 94, MUTED, 14, anchor_x="center")
        arcade.draw_text("ENTER also works if SPACE feels ignored", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 72, MUTED, 11, anchor_x="center")
        self.shop_bounds = []
        for idx, (item, label, cost, rarity) in enumerate(self.shop_options):
            y = SCREEN_HEIGHT / 2 + 38 - idx * 72
            left = SCREEN_WIDTH / 2 - 330
            bottom = y - 28
            right = SCREEN_WIDTH / 2 + 330
            top = y + 28
            self.shop_bounds.append((left, right, bottom, top))
            affordable = self.player.money >= cost
            fill = arcade.color.DARK_GREEN if affordable else arcade.color.DARK_RED
            arcade.draw_lbwh_rectangle_filled(left, bottom, 660, 56, fill)
            arcade.draw_lbwh_rectangle_outline(left, bottom, 660, 56, arcade.color.WHITE, 2)
            title = f"{idx + 1}. {label} [{rarity}]"
            arcade.draw_text(title, left + 18, y + 8, TEXT, 16)
            arcade.draw_text(f"${cost}", left + 560, y + 8, TEXT, 16)
            arcade.draw_text(item, left + 18, y - 14, MUTED, 11)

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
            stats = f"HP +{outfit.max_health_bonus}  DMG +{outfit.damage_bonus}  SPD +{outfit.speed_bonus}  Sustainability {outfit.sustainability:+d}"
            arcade.draw_text(stats, left + 86, y - 28, arcade.color.BLACK, 10)


def main() -> None:
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    view = GameView()
    window.show_view(view)
    arcade.run()


if __name__ == "__main__":
    main()
