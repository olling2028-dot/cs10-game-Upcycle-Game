# ...existing code...
"""Hunter & Ollin serious game MVP.

This version turns the design doc into a small playable vertical slice:
- Move through the build
- Fight enemies with basic attacks
- Collect weapon and armor drops after every floor
- Swap gear in an inventory instead of using a shop
- Defeat the CEO boss and keep climbing forever
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional

import arcade

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
SCREEN_TITLE = "Hunter & Ollin - Upcycle Game MVP"

PLAYER_SPEED = 5
ATTACK_COOLDOWN = 0.16
ATTACK_RANGE = 100
ATTACK_DAMAGE = 18
ATTACK_BOX_LENGTH = 84
ATTACK_BOX_WIDTH = 56
PLAYER_HITBOX_WIDTH = 34
PLAYER_HITBOX_HEIGHT = 48
ENEMY_HITBOX_SCALE = 0.82
ENEMY_TOUCH_PADDING = 2
BOSS_HITBOX_WIDTH = 88
BOSS_HITBOX_HEIGHT = 98
PUNCH_ANIMATION_TIME = 0.1
LUNGE_SPECIAL_COOLDOWN = 0.32
SWEEP_SPECIAL_COOLDOWN = 2.58
SLAM_SPECIAL_COOLDOWN = 8.0
PULSE_SPECIAL_COOLDOWN = 3.3
LUNGE_DASH_DISTANCE = 88
LUNGE_DASH_TIME = 0.14
SLAM_STUN_TIME = 1.0
BASE_PLAYER_MAX_HEALTH = 120
BASE_PLAYER_SPEED = 5
BASE_PLAYER_DAMAGE = 18
BASE_PLAYER_DEFENSE = 0
MALAISE_MAX = 100.0
MALAISE_GAIN_RATE = 0.24
MALAISE_RECOVERY_RATE = 0.05
MALAISE_DAMAGE_INTERVAL = 2.4
MALAISE_TICK_THRESHOLD = 55.0
MALAISE_TICK_DAMAGE = 2
MALAISE_KILL_RECOVERY = 10.0
MALAISE_PASSIVE_RECOVERY = 0.03
MALAISE_HIT_MULTIPLIER = 0.8
MALAISE_HIT_MINIMUM = 1.5

BACKGROUND = arcade.color.DARK_SLATE_GRAY
PANEL = arcade.color.DARK_BROWN
TEXT = arcade.color.WHITE
MUTED = arcade.color.LIGHT_GRAY
GOOD = arcade.color.AMAZON
BAD = arcade.color.RED_ORANGE

PLAYER_TEXTURE_FILES = {
    "default": "images/Main_char.png",
    "cool": "images/Main_cool_char.png",
    "winter": "images/Main_char_winter.png",
}

ENEMY_TEXTURE_FILES = {
    "slime": "images/Slime.png",
    "zombie": "images/Zombie.png",
    "zombie_orange": "images/Zombie_orange.png",
    "ogre": "images/Oger.png",
}

BOSS_TEXTURE_FILES = {
    "robo": "images/Robo_boss.png",
    "western": "images/Western_Boss.png",
    "meatball": "images/Robo_Meatball.png",
}

WEAPON_TEMPLATES = [
    ("Rebar", "Blade", 6, 1, 0, "basic", (100, 149, 237)),
    ("Bottle", "Spear", 5, 0, 1, "lunge", (135, 206, 235)),
    ("Patchwork", "Hammer", 8, -1, 0, "sweep", (70, 130, 180)),
    ("Circuit", "Cutter", 7, 0, -1, "sweep", (64, 224, 208)),
    ("Scrap", "Bracer", 4, 2, 1, "lunge", (54, 117, 136)),
    ("Tin", "Halberd", 6, 1, 2, "pierce", (176, 224, 230)),
    ("Rivet", "Maul", 9, -2, -1, "slam", (205, 92, 92)),
    ("Carbon", "Fork", 5, 1, 0, "pulse", (32, 178, 170)),
]

ARMOR_TEMPLATES = [
    ("Reclaimed", "Vest", 2, 8, 2, (255, 191, 0)),
    ("Padded", "Coat", 1, 10, 1, (255, 179, 71)),
    ("Canvas", "Guard", 3, 6, 3, (244, 164, 96)),
    ("Thrifted", "Shell", 4, 5, 0, (205, 127, 50)),
    ("Reinforced", "Wrap", 2, 9, -1, (245, 245, 220)),
]


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


# Simple equipment item (weapon/armor)
@dataclass
class Item:
    name: str
    type: str  # "weapon" or "armor"
    description: str = ""
    damage_bonus: int = 0
    defense_bonus: int = 0
    max_health_bonus: int = 0
    sustainability: int = 0
    weapon_style: str = ""
    rarity: str = "common"
    legendary_ability: str = ""
    color: arcade.Color = arcade.color.LIGHT_GRAY

    @property
    def rating(self) -> int:
        if self.type == "weapon":
            return max(1, self.damage_bonus * 2 + max(0, self.sustainability) + self.defense_bonus + self.max_health_bonus // 4)
        return max(1, self.defense_bonus * 2 + self.max_health_bonus // 3 + max(0, self.sustainability) + self.damage_bonus // 2)

    @property
    def type_label(self) -> str:
        return "Weapon" if self.type == "weapon" else "Armor"

    @property
    def type_color(self) -> arcade.Color:
        return arcade.color.CYAN if self.type == "weapon" else arcade.color.ORANGE

    @property
    def is_legendary(self) -> bool:
        return self.rarity == "legendary"

    @property
    def summary(self) -> str:
        parts: list[str] = []
        if self.type == "weapon":
            parts.append(f"+{self.damage_bonus} dmg")
            if self.sustainability:
                parts.append(f"{self.sustainability:+d} sustainability")
        else:
            parts.append(f"+{self.defense_bonus} def")
            parts.append(f"+{self.max_health_bonus} hp")
            if self.sustainability:
                parts.append(f"{self.sustainability:+d} sustainability")
        if self.is_legendary:
            parts.append("LEGENDARY")
        return " | ".join(parts)


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
        self.visual_theme = "default"
        self.unlocked_attacks: set[str] = {"basic"}
        self.max_health = self.base_max_health
        self.health = self.max_health

        # Inventory and equipment
        self.inventory: list[Item] = []
        self.equipped_weapon: Optional[Item] = None
        self.equipped_armor: Optional[Item] = None

    @property
    def damage(self) -> int:
        outfit_bonus = sum(o.damage_bonus for o in self.outfits)
        weapon_bonus = (self.equipped_weapon.damage_bonus if self.equipped_weapon else 0)
        armor_bonus = (self.equipped_armor.damage_bonus if self.equipped_armor else 0)
        legendary_bonus = 0
        if self.equipped_armor and self.equipped_armor.is_legendary:
            if self.equipped_armor.legendary_ability == "cool":
                legendary_bonus += 2
            elif self.equipped_armor.legendary_ability == "winter":
                legendary_bonus += 1
        return self.base_damage + outfit_bonus + weapon_bonus + armor_bonus + legendary_bonus

    @property
    def speed(self) -> int:
        legendary_bonus = 0
        if self.equipped_armor and self.equipped_armor.is_legendary and self.equipped_armor.legendary_ability == "cool":
            legendary_bonus += 1
        return self.base_speed + sum(o.speed_bonus for o in self.outfits) + legendary_bonus

    @property
    def sustainability(self) -> int:
        equip_sustain = 0
        if self.equipped_weapon:
            equip_sustain += self.equipped_weapon.sustainability
        if self.equipped_armor:
            equip_sustain += self.equipped_armor.sustainability
        return sum(o.sustainability for o in self.outfits) + equip_sustain

    @property
    def microplastics_stage(self) -> int:
        return min(3, int(self.microplastics // 25))

    @property
    def effective_damage(self) -> int:
        # account for microplastics penalties
        return max(1, self.damage - self.microplastics_stage * 2)

    @property
    def effective_speed(self) -> int:
        return max(2, self.speed - self.microplastics_stage)

    def refresh_stats(self) -> None:
        previous_max_health = self.max_health
        bonus_health = sum(o.max_health_bonus for o in self.outfits)
        equip_hp = 0
        equip_def = 0
        equip_speed = 0
        equip_damage = 0
        if self.equipped_armor:
            equip_hp += self.equipped_armor.max_health_bonus
            equip_def += self.equipped_armor.defense_bonus
            equip_speed += self.equipped_armor.speed_bonus if hasattr(self.equipped_armor, "speed_bonus") else 0
            equip_damage += self.equipped_armor.damage_bonus
            if self.equipped_armor.is_legendary and self.equipped_armor.legendary_ability == "winter":
                equip_hp += 12
                equip_def += 2
        self.max_health = self.base_max_health + bonus_health + equip_hp
        self.defense = BASE_PLAYER_DEFENSE + sum(o.defense_bonus for o in self.outfits) + equip_def
        if self.max_health > previous_max_health:
            self.health += self.max_health - previous_max_health
        self.health = min(self.health, self.max_health)

    def apply_pickup_visuals(self, item: Item) -> None:
        """Keep pickup visuals tied to equipped gear instead of loose inventory loot."""
        return

    def update_visual_theme_from_equipment(self) -> None:
        weapon = self.equipped_weapon
        armor = self.equipped_armor
        equipped_items = [item for item in (weapon, armor) if item is not None]
        for item in equipped_items:
            item_name = item.name.lower()
            item_description = item.description.lower()
            if "winter" in item_name or "winter" in item_description:
                self.visual_theme = "winter"
                return
            if "cool" in item_name or "cool" in item_description:
                self.visual_theme = "cool"
                return
        self.visual_theme = "default"

    @property
    def legendary_armor_ability(self) -> str:
        if self.equipped_armor and self.equipped_armor.is_legendary:
            return self.equipped_armor.legendary_ability
        return ""


class Enemy(Entity):
    def __init__(self, x: float, y: float, floor: int):
        self.variant = self.pick_variant(floor)
        # Keep early floors approachable and let difficulty rise more gradually.
        size = 34 + floor
        if self.variant == "slime":
            size = int(size * 1.05)
        elif self.variant == "ogre":
            size = int(size * 1.18)
        super().__init__(x, y, size, size, arcade.color.FIREBRICK)
        self.max_health = 38 + floor * 12
        self.health = self.max_health
        self.speed = 1.15 + floor * 0.16
        self.touch_damage = 7 + floor * 1
        self.stun_timer = 0.0
        self.ai_timer = 0.0
        self.ai_state = "idle"
        if self.variant == "slime":
            self.max_health = int(self.max_health * 2.1)
            self.health = self.max_health
            self.speed *= 0.55
            self.touch_damage = max(1, int(self.touch_damage * 0.95))
            self.ai_timer = random.uniform(0.9, 1.7)
        elif self.variant == "zombie":
            self.max_health = int(self.max_health * 1.15)
            self.health = self.max_health
            self.speed *= 0.98
        elif self.variant == "zombie_orange":
            self.max_health = int(self.max_health * 1.2)
            self.health = self.max_health
            self.speed *= 1.06
            self.touch_damage = int(self.touch_damage * 1.08)
        elif self.variant == "ogre":
            self.speed *= 1.45
            self.max_health = int(self.max_health * 1.28)
            self.health = self.max_health
            self.touch_damage = int(self.touch_damage * 1.25)

    @staticmethod
    def pick_variant(floor: int) -> str:
        # Floors now mix enemy types instead of locking one variant per floor.
        weights = [
            ("slime", 4 + max(0, 3 - floor // 3)),
            ("zombie", 3 + floor // 4),
            ("zombie_orange", 2 + floor // 5),
            ("ogre", 1 + floor // 6),
        ]
        variants = [variant for variant, weight in weights for _ in range(weight)]
        return random.choice(variants)


class Boss(Entity):
    def __init__(self, variant: str = "western"):
        size = 102 if variant == "meatball" else 126
        super().__init__(SCREEN_WIDTH / 2, SCREEN_HEIGHT - 180, size, size, arcade.color.PURPLE)
        self.variant = variant
        self.max_health = 180 if variant == "meatball" else 320
        self.health = self.max_health
        self.speed = 1.45 if variant == "meatball" else 1.75
        self.touch_damage = 12 if variant == "meatball" else 18
        self.projectile_cooldown = 0.0


class Projectile(Entity):
    def __init__(self, x: float, y: float, dx: float, dy: float, speed: float, damage: int, color: arcade.Color):
        super().__init__(x, y, 12, 12, color)
        self.dx = dx
        self.dy = dy
        self.speed = speed
        self.damage = damage
        self.life = 3.0


class GameView(arcade.View):
    def __init__(self) -> None:
        super().__init__()
        self.state = "intro"
        self.player = Player(160, 160)
        self.enemies: list[Enemy] = []
        self.enemy_projectiles: list[Projectile] = []
        self.boss_projectiles: list[Projectile] = []
        self.boss = Boss()
        self.pressed_keys: set[int] = set()
        self.mouse_x = self.player.x
        self.mouse_y = self.player.y
        self.attack_flash = 0.0
        self.punch_timer = 0.0
        self.special_attack_timer = 0.0
        self.special_attack_effect = ""
        self.special_attack_effect_timer = 0.0
        self.lunge_dash_timer = 0.0
        self.lunge_dash_dx = 0.0
        self.lunge_dash_dy = 0.0
        self._last_delta_time = 1 / 60
        self.damage_flash = 0.0
        self.screen_shake = 0.0
        self.current_message = "Press ENTER to start the climb."
        # inventory UI
        self.inv_bounds: list[tuple[float, float, float, float]] = []
        self.inventory_slots: list[tuple[float, float, float, float]] = []
        self.equipment_slots: dict[str, tuple[float, float, float, float]] = {}
        self.dragged_item_index: Optional[int] = None
        self.dragged_item_source: str = ""
        self.dragged_item_offset_x = 0.0
        self.dragged_item_offset_y = 0.0
        self.dragged_item_mouse_x = 0.0
        self.dragged_item_mouse_y = 0.0
        self.dragged_item_label = ""
        self.dragged_from_equipment: Optional[str] = None
        self.inventory_dragging = False
        self.dragged_from_inventory_index: Optional[int] = None
        self.hovered_inventory_index: Optional[int] = None
        self.floor_loot: list[Item] = []
        self.microplastics_effect_timer = 0.0
        self.microplastics_effect_title = ""
        self.microplastics_effect_body = ""
        self._last_microplastics_stage = self.player.microplastics_stage
        self.player_textures = self.load_player_textures()
        self.enemy_textures = self.load_textures(ENEMY_TEXTURE_FILES)
        self.boss_textures = self.load_textures(BOSS_TEXTURE_FILES)
        self.floor_texture = self.load_textures({"floor": "images/floor.PNG"}).get("floor")

    def on_show_view(self) -> None:
        arcade.set_background_color(BACKGROUND)

    def load_player_textures(self) -> dict[str, arcade.Texture]:
        return self.load_textures(PLAYER_TEXTURE_FILES)

    def load_textures(self, mapping: dict[str, str]) -> dict[str, arcade.Texture]:
        textures: dict[str, arcade.Texture] = {}
        for key, path in mapping.items():
            try:
                textures[key] = arcade.load_texture(path)
            except Exception:
                continue
        return textures

    def spawn_floor(self) -> None:
        self.floor_loot = []
        self.enemy_projectiles = []
        self.boss_projectiles = []
        if self.player.floor % 4 == 0:
            self.state = "boss"
            if self.player.floor % 8 == 0:
                boss_variant = "robo"
            elif self.player.floor % 8 == 4:
                boss_variant = "meatball"
            else:
                boss_variant = "western"
            self.boss = Boss(boss_variant)
            self.boss.x = SCREEN_WIDTH / 2
            self.boss.y = SCREEN_HEIGHT - 160
            if boss_variant == "meatball":
                self.current_message = "A meatball prototype rolls in as a mini boss."
            elif boss_variant == "robo":
                self.current_message = "The robo boss powers up and starts firing projectiles."
            else:
                self.current_message = "The western boss rides in as the CEO's final form."
            return
        self.enemies = []
        for _ in range(2 + self.player.floor):
            x, y = self.random_enemy_spawn_point()
            self.enemies.append(Enemy(x, y, self.player.floor))
        self.state = "combat"

    def open_inventory(self, message: str | None = None) -> None:
        self.state = "inventory"
        if message is None:
            self.current_message = "Inventory: drag items to the weapon or armor slot. Close with I or SPACE."
        else:
            self.current_message = message
        self.pressed_keys.clear()
        self.clear_drag_state()

    def draw_wrapped_text(
        self,
        text: str,
        x: float,
        y: float,
        color: arcade.Color,
        size: int,
        width: float,
        anchor_x: str = "left",
        align: str = "left",
    ) -> None:
        if not text:
            return

        # Arcade's width handling can still leave long labels awkwardly clipped in this layout,
        # so we do a simple word-wrap pass ourselves and draw line by line.
        words = text.split()
        if not words:
            return

        lines: list[str] = []
        current = words[0]
        approx_char_width = max(1.0, size * 0.58)
        max_chars = max(1, int(width / approx_char_width))

        for word in words[1:]:
            if len(word) > max_chars:
                if current:
                    lines.append(current)
                chunk = word
                while len(chunk) > max_chars:
                    lines.append(chunk[: max_chars - 1] + "...")
                    chunk = chunk[max_chars - 1 :]
                current = chunk
                continue
            candidate = f"{current} {word}"
            if len(candidate) <= max_chars:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)

        line_height = size + 2
        total_height = line_height * len(lines)
        start_y = y + total_height / 2 - line_height
        for i, line in enumerate(lines):
            line_y = start_y - i * line_height
            arcade.draw_text(line, x, line_y, color, size, anchor_x=anchor_x, align=align)

    def compact_label(self, text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        if max_chars <= 3:
            return text[:max_chars]
        return text[: max_chars - 1] + "..."

    def fit_font_size(self, text: str, max_width: float, max_size: int, min_size: int = 8) -> int:
        """Pick a font size that should fit the requested width."""
        if not text:
            return min_size
        estimated_size = int(max_width / (len(text) * 0.58))
        return max(min_size, min(max_size, estimated_size))

    def draw_text_with_shadow(
        self,
        text: str,
        x: float,
        y: float,
        color: arcade.Color,
        size: int,
        width: float | None = None,
        anchor_x: str = "left",
        align: str = "left",
    ) -> None:
        shadow_color = arcade.color.BLACK
        if width is None:
            arcade.draw_text(text, x + 1, y - 1, shadow_color, size, anchor_x=anchor_x, align=align)
            arcade.draw_text(text, x, y, color, size, anchor_x=anchor_x, align=align)
        else:
            arcade.draw_text(text, x + 1, y - 1, shadow_color, size, anchor_x=anchor_x, align=align, width=width)
            arcade.draw_text(text, x, y, color, size, anchor_x=anchor_x, align=align, width=width)

    def draw_fitted_text(
        self,
        text: str,
        x: float,
        y: float,
        color: arcade.Color,
        max_width: float,
        max_size: int,
        min_size: int = 8,
        anchor_x: str = "left",
        align: str = "left",
    ) -> None:
        if not text:
            return
        size = self.fit_font_size(text, max_width, max_size, min_size)
        arcade.draw_text(text, x + 1, y - 1, arcade.color.BLACK, size, anchor_x=anchor_x, align=align, width=max_width)
        arcade.draw_text(text, x, y, color, size, anchor_x=anchor_x, align=align, width=max_width)

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

        if self.state == "inventory":
            # equip by number
            if key in {arcade.key.KEY_1, arcade.key.NUM_1}:
                self.equip_from_inventory(0)
            elif key in {arcade.key.KEY_2, arcade.key.NUM_2}:
                self.equip_from_inventory(1)
            elif key in {arcade.key.KEY_3, arcade.key.NUM_3}:
                self.equip_from_inventory(2)
            elif key in {arcade.key.KEY_4, arcade.key.NUM_4}:
                self.equip_from_inventory(3)
            elif key in {arcade.key.KEY_5, arcade.key.NUM_5}:
                self.equip_from_inventory(4)
            elif key in {arcade.key.ENTER, arcade.key.I}:
                # close inventory and continue
                self.player.refresh_stats()
                if self.enemies:
                    self.state = "combat"
                    self.current_message = "Back to the climb."
                else:
                    self.spawn_floor()
                    self.current_message = "Back to the climb."
            return

        if self.state in {"combat", "boss"} and key == arcade.key.SPACE:
            if self.player.attack_timer <= 0:
                self.attack()
        if self.state in {"combat", "boss"} and key in {arcade.key.Q, arcade.key.E, arcade.key.R, arcade.key.T, arcade.key.Y}:
            self.special_attack(key)

        # allow quick inventory open
        if key == arcade.key.I:
            self.open_inventory()

    def on_key_release(self, key: int, modifiers: int) -> None:
        self.pressed_keys.discard(key)

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> None:
        if self.state != "inventory" or button != arcade.MOUSE_BUTTON_LEFT:
            return
        self.dragged_item_mouse_x = x
        self.dragged_item_mouse_y = y
        inventory_idx = self.inventory_slot_for_position(x, y)
        if inventory_idx is not None:
            self.begin_drag_inventory(inventory_idx, x, y)
            return
        for slot_name, bounds in self.equipment_slots.items():
            left, right, bottom, top = bounds
            if left <= x <= right and bottom <= y <= top:
                self.begin_drag_equipped(slot_name, x, y)
                return

    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int) -> None:
        if self.state != "inventory" or button != arcade.MOUSE_BUTTON_LEFT:
            return
        self.dragged_item_mouse_x = x
        self.dragged_item_mouse_y = y
        self.finish_drag(x, y)

    def attack(self) -> None:
        self.player.attack_timer = ATTACK_COOLDOWN
        self.attack_flash = 0.12
        self.punch_timer = PUNCH_ANIMATION_TIME
        # Aim the punch directly toward the cursor so the hitbox lines up with the reticle.
        aim_x = self.mouse_x - self.player.x
        aim_y = self.mouse_y - self.player.y
        aim_len = math.hypot(aim_x, aim_y)
        if aim_len == 0:
            aim_x, aim_y = 1.0, 0.0
            aim_len = 1.0
        self.player.facing_x = aim_x / aim_len
        self.player.facing_y = aim_y / aim_len
        attack_box = self.attack_rect()
        targets = self.enemies if self.state == "combat" else [self.boss]
        hit = False
        damage = self.player.effective_damage
        if self.player.equipped_weapon and self.player.equipped_weapon.weapon_style == "sweep":
            damage += 2
        if self.player.equipped_weapon and self.player.equipped_weapon.weapon_style == "lunge":
            damage += 2
        if self.player.equipped_weapon and self.player.equipped_weapon.weapon_style == "pierce":
            damage += 1
        for target in list(targets):
            if self.rects_intersect(attack_box, self.entity_hitbox(target, 0.0)):
                self.damage_target(target, damage)
                hit = True
        if hit:
            self.screen_shake = 0.08
        else:
            self.current_message = "No target in range. Move closer."

    def special_attack(self, key: int) -> None:
        if self.special_attack_timer > 0:
            self.current_message = f"Special on cooldown: {self.special_attack_timer:.1f}s left."
            return
        weapon_style = self.player.equipped_weapon.weapon_style if self.player.equipped_weapon else ""
        has_sweep = weapon_style == "sweep"
        has_lunge = weapon_style == "lunge"
        has_pierce = weapon_style == "pierce"
        has_slam = weapon_style == "slam"
        has_pulse = weapon_style == "pulse"
        if key == arcade.key.Q and has_sweep:
            self.special_attack_timer = SWEEP_SPECIAL_COOLDOWN
            self.special_attack_effect = "sweep"
            self.special_attack_effect_timer = 0.45
            self.current_message = f"Sweep attack with {self.player.equipped_weapon.name}!"
            targets = self.enemies if self.state == "combat" else [self.boss]
            hit = False
            # Determine sweep direction (aim at cursor, fallback to facing)
            aim_x = self.mouse_x - self.player.x
            aim_y = self.mouse_y - self.player.y
            if abs(aim_x) < 1e-3 and abs(aim_y) < 1e-3:
                aim_x = self.player.facing_x
                aim_y = self.player.facing_y
            aim_len = math.hypot(aim_x, aim_y) or 1.0
            aim_x /= aim_len
            aim_y /= aim_len
            SWEEP_RANGE = 220
            SWEEP_ANGLE_DEG = 180
            sweep_damage = max(1, self.player.effective_damage - 1)
            if self.player.legendary_armor_ability == "cool":
                SWEEP_RANGE += 24
                SWEEP_ANGLE_DEG += 10
                sweep_damage += 2
            cos_thresh = math.cos(math.radians(SWEEP_ANGLE_DEG / 2))
            for target in list(targets):
                dx = target.x - self.player.x
                dy = target.y - self.player.y
                dist = math.hypot(dx, dy)
                if dist <= SWEEP_RANGE:
                    dot = (dx * aim_x + dy * aim_y) / (dist or 1.0)
                    target_box = self.entity_hitbox(target, 0.0)
                    target_radius = max(target_box[1] - target_box[0], target_box[3] - target_box[2]) * 0.5
                    if dot >= cos_thresh - 0.08 and dist <= SWEEP_RANGE + target_radius * 0.45:
                        self.damage_target(target, sweep_damage)
                        hit = True
            if hit:
                self.screen_shake = 0.1
            return
        if key == arcade.key.E and has_lunge:
            self.special_attack_timer = LUNGE_SPECIAL_COOLDOWN
            self.special_attack_effect = "lunge"
            self.special_attack_effect_timer = 0.26
            self.player.invuln_timer = 1.0
            self.current_message = f"Lunge strike with {self.player.equipped_weapon.name}!"
            # Lunge toward the pointer
            aim_x = self.mouse_x - self.player.x
            aim_y = self.mouse_y - self.player.y
            aim_len = math.hypot(aim_x, aim_y)
            if aim_len == 0:
                aim_x, aim_y = 1.0, 0.0
                aim_len = 1.0
            self.lunge_dash_dx = aim_x / aim_len
            self.lunge_dash_dy = aim_y / aim_len
            # Set 8-direction facing from dash vector so visuals follow the pointer
            def sign(v: float) -> int:
                return 1 if v > 0 else -1 if v < 0 else 0

            self.player.facing_x = float(sign(self.lunge_dash_dx))
            self.player.facing_y = float(sign(self.lunge_dash_dy))
            self.lunge_dash_timer = LUNGE_DASH_TIME
            start_x = self.player.x
            start_y = self.player.y
            end_x = start_x + self.lunge_dash_dx * LUNGE_DASH_DISTANCE
            end_y = start_y + self.lunge_dash_dy * LUNGE_DASH_DISTANCE
            self.player.x += self.lunge_dash_dx * LUNGE_DASH_DISTANCE * 0.35
            self.player.y += self.lunge_dash_dy * LUNGE_DASH_DISTANCE * 0.35
            targets = self.enemies if self.state == "combat" else [self.boss]
            hit = False
            lunge_damage = self.player.effective_damage + 8
            if self.player.legendary_armor_ability == "winter":
                lunge_damage += 2
            for target in list(targets):
                target_box = self.entity_hitbox(target, 0.0)
                target_cx = (target_box[0] + target_box[1]) / 2
                target_cy = (target_box[2] + target_box[3]) / 2
                target_radius = max(target_box[1] - target_box[0], target_box[3] - target_box[2]) * 0.5
                if self.distance_point_to_segment(target_cx, target_cy, start_x, start_y, end_x, end_y) <= target_radius + 48:
                    self.damage_target(target, lunge_damage)
                    hit = True
            if hit:
                self.screen_shake = 0.1
            return
        if key == arcade.key.R and has_pierce:
            self.special_attack_timer = 3.15
            self.special_attack_effect = "pierce"
            self.special_attack_effect_timer = 0.32
            self.current_message = f"Pierce attack with {self.player.equipped_weapon.name}!"
            targets = self.enemies if self.state == "combat" else [self.boss]
            hit = False
            aim_x = self.mouse_x - self.player.x
            aim_y = self.mouse_y - self.player.y
            if abs(aim_x) < 1e-3 and abs(aim_y) < 1e-3:
                aim_x = self.player.facing_x
                aim_y = self.player.facing_y
            aim_len = math.hypot(aim_x, aim_y) or 1.0
            aim_x /= aim_len
            aim_y /= aim_len
            self.player.facing_x = aim_x
            self.player.facing_y = aim_y
            for target in list(targets):
                dx = target.x - self.player.x
                dy = target.y - self.player.y
                dist = math.hypot(dx, dy)
                if dist <= 260:
                    dot = (dx * aim_x + dy * aim_y) / (dist or 1.0)
                    if dot > 0.72:
                        self.damage_target(target, self.player.effective_damage + 4)
                        hit = True
            if hit:
                self.screen_shake = 0.08
            return
        if key == arcade.key.T and has_slam:
            self.special_attack_timer = SLAM_SPECIAL_COOLDOWN
            self.special_attack_effect = "slam"
            self.special_attack_effect_timer = 0.36
            self.current_message = f"Slam attack with {self.player.equipped_weapon.name}!"
            targets = self.enemies if self.state == "combat" else [self.boss]
            hit = False
            slam_damage = self.player.effective_damage + 6
            for target in list(targets):
                dx = target.x - self.player.x
                dy = target.y - self.player.y
                if math.hypot(dx, dy) <= 170:
                    self.damage_target(target, slam_damage)
                    self.stun_enemy(target)
                    hit = True
            if hit:
                self.screen_shake = 0.14
            return
        if key == arcade.key.Y and has_pulse:
            self.special_attack_timer = PULSE_SPECIAL_COOLDOWN
            self.special_attack_effect = "pulse"
            self.special_attack_effect_timer = 0.4
            self.current_message = f"Pulse attack with {self.player.equipped_weapon.name}!"
            targets = self.enemies if self.state == "combat" else [self.boss]
            hit = False
            for target in list(targets):
                dx = target.x - self.player.x
                dy = target.y - self.player.y
                dist = math.hypot(dx, dy)
                if dist <= 210:
                    self.damage_target(target, max(1, self.player.effective_damage + 2))
                    hit = True
            if hit:
                self.screen_shake = 0.1

    def attack_rect(self) -> tuple[float, float, float, float]:
        length = ATTACK_BOX_LENGTH
        width = ATTACK_BOX_WIDTH

        fx = self.player.facing_x
        fy = self.player.facing_y
        if fx == 0 and fy == 0:
            fx = 1.0

        facing_len = math.hypot(fx, fy) or 1.0
        fx /= facing_len
        fy /= facing_len

        # Build a forward-facing attack box centered just beyond the player's body.
        forward_offset = self.player.width / 2 + length / 2 - 2
        center_x = self.player.x + fx * forward_offset
        center_y = self.player.y + fy * forward_offset

        # Convert the oriented rectangle into an axis-aligned bounds box for collision checks.
        half_forward = length / 2
        half_side = width / 2
        perp_x = -fy
        perp_y = fx

        corners = (
            (center_x + fx * half_forward + perp_x * half_side, center_y + fy * half_forward + perp_y * half_side),
            (center_x + fx * half_forward - perp_x * half_side, center_y + fy * half_forward - perp_y * half_side),
            (center_x - fx * half_forward + perp_x * half_side, center_y - fy * half_forward + perp_y * half_side),
            (center_x - fx * half_forward - perp_x * half_side, center_y - fy * half_forward - perp_y * half_side),
        )
        xs = [point[0] for point in corners]
        ys = [point[1] for point in corners]
        return min(xs), max(xs), min(ys), max(ys)

    def distance_point_to_segment(
        self,
        px: float,
        py: float,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> float:
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        return math.hypot(px - closest_x, py - closest_y)

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float) -> None:
        self.mouse_x = x
        self.mouse_y = y
        if self.state == "inventory":
            self.hovered_inventory_index = self.inventory_slot_for_position(x, y)
        else:
            self.hovered_inventory_index = None
        if self.inventory_dragging:
            self.dragged_item_mouse_x = x
            self.dragged_item_mouse_y = y

    def entity_hitbox(self, entity: Entity, padding: float = 0.0) -> tuple[float, float, float, float]:
        if isinstance(entity, Boss):
            return self.boss_hitbox(padding)
        if isinstance(entity, Player):
            width = PLAYER_HITBOX_WIDTH
            height = PLAYER_HITBOX_HEIGHT
            left, right, bottom, top = entity.x - width / 2, entity.x + width / 2, entity.y - height / 2, entity.y + height / 2
            return left + padding, right - padding, bottom + padding, top - padding
        width = entity.width * ENEMY_HITBOX_SCALE
        height = entity.height * ENEMY_HITBOX_SCALE
        left, right, bottom, top = entity.x - width / 2, entity.x + width / 2, entity.y - height / 2, entity.y + height / 2
        return left + padding, right - padding, bottom + padding, top - padding

    def boss_hitbox(self, padding: float = 0.0) -> tuple[float, float, float, float]:
        # Tighter than the rendered boss so hits feel aligned with the body.
        width = BOSS_HITBOX_WIDTH
        height = BOSS_HITBOX_HEIGHT
        left = self.boss.x - width / 2
        right = self.boss.x + width / 2
        bottom = self.boss.y - height / 2
        top = self.boss.y + height / 2
        return left + padding, right - padding, bottom + padding, top - padding

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
        # small knockback clamp
        target.x = max(40, min(SCREEN_WIDTH - 40, target.x))
        target.y = max(40, min(SCREEN_HEIGHT - 40, target.y))

    def stun_enemy(self, target: Entity, duration: float = SLAM_STUN_TIME) -> None:
        if isinstance(target, Enemy):
            target.stun_timer = max(target.stun_timer, duration)

    def on_update(self, delta_time: float) -> None:
        if self.state == "game_over":
            return
        self._last_delta_time = delta_time

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

        self.update_microplastics(delta_time)

        dx = dy = 0
        if arcade.key.LEFT in self.pressed_keys or ord("a") in self.pressed_keys or ord("A") in self.pressed_keys:
            dx -= 1
        if arcade.key.RIGHT in self.pressed_keys or ord("d") in self.pressed_keys or ord("D") in self.pressed_keys:
            dx += 1
        if arcade.key.UP in self.pressed_keys or ord("w") in self.pressed_keys or ord("W") in self.pressed_keys:
            dy += 1
        if arcade.key.DOWN in self.pressed_keys or ord("s") in self.pressed_keys or ord("S") in self.pressed_keys:
            dy -= 1

        magnitude = math.hypot(dx, dy)
        if magnitude:
            dx /= magnitude
            dy /= magnitude
            # Do not let movement override facing while an attack or special effect is animating.
            if self.punch_timer <= 0 and self.special_attack_effect_timer <= 0:
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
                self.finish_floor()
        elif self.state == "boss":
            self.update_boss()
            if self.boss.health <= 0:
                self.finish_floor(boss=True)
        self.update_projectiles(delta_time)

    def finish_floor(self, boss: bool = False) -> None:
        all_loot = [self.generate_drop(self.player.floor, boss=boss)]
        self.floor_loot = []
        self.player.inventory.extend(all_loot)
        for drop in all_loot:
            self.player.apply_pickup_visuals(drop)
        self.player.money += 8 + self.player.floor * 2
        self.player.floor += 1
        self.player.refresh_stats()
        message = f"Floor cleared. Loot moved to inventory. Open inventory (I)."
        self.open_inventory(message)

    def generate_drop(self, floor: int, boss: bool = False) -> Item:
        special_roll = random.random()
        legendary_chance = 0.025 if not boss else 0.06
        if special_roll < legendary_chance:
            return Item(
                name="Legendary Cool Jacket",
                type="armor",
                description="A stylish upcycled jacket that makes the whole build feel cooler.",
                damage_bonus=6,
                defense_bonus=6,
                max_health_bonus=24,
                sustainability=9,
                rarity="legendary",
                legendary_ability="cool",
                color=arcade.color.DEEP_SKY_BLUE,
            )
        if special_roll < legendary_chance * 2:
            return Item(
                name="Legendary Winter Coat",
                type="armor",
                description="Warm layered protection that gives the hero a winter look.",
                damage_bonus=0,
                defense_bonus=12,
                max_health_bonus=42,
                sustainability=6,
                rarity="legendary",
                legendary_ability="winter",
                color=arcade.color.LIGHT_BLUE,
            )

        # Bias drops more toward armor so the appearance-changing gear shows up more often.
        typ = random.choices(["weapon", "armor"], weights=[30, 70], k=1)[0]
        level = max(1, floor // 2)
        if boss:
            level += 2
        if typ == "weapon":
            prefix, suffix, base_damage, base_sustain, base_sustain_bonus, weapon_style, color = random.choice(WEAPON_TEMPLATES)
            quality = level + random.randint(0, 2)
            damage_bonus = base_damage + quality
            sustain = base_sustain + base_sustain_bonus + random.randint(-1, 1) + (1 if boss else 0)
            return Item(
                name=f"{prefix} {suffix} +{level}",
                type="weapon",
                description=f"A recycled {suffix.lower()} built for {weapon_style} combat.",
                damage_bonus=damage_bonus,
                defense_bonus=0,
                max_health_bonus=0,
                sustainability=sustain,
                weapon_style=weapon_style,
                color=color,
            )
        prefix, suffix, base_defense, base_hp, base_sustain, color = random.choice(ARMOR_TEMPLATES)
        quality = level + random.randint(0, 2)
        defense_bonus = base_defense + quality // 2
        max_health_bonus = base_hp + quality * 2
        sustain = base_sustain + random.randint(0, 2)
        return Item(
            name=f"{prefix} {suffix} +{level}",
            type="armor",
            description="Upcycled protection that softens hits and steadies the suit.",
            damage_bonus=0,
            defense_bonus=defense_bonus,
            max_health_bonus=max_health_bonus,
            sustainability=sustain,
            color=color,
        )

    def draw_ui(self) -> None:
        arcade.draw_lrbt_rectangle_filled(18, 420, SCREEN_HEIGHT - 150, SCREEN_HEIGHT - 18, PANEL)
        self.draw_text_with_shadow(f"Health: {self.player.health}/{self.player.max_health}", 30, SCREEN_HEIGHT - 56, TEXT, 16)
        self.draw_text_with_shadow(f"Floor: {self.player.floor}", 30, SCREEN_HEIGHT - 82, TEXT, 16)
        stat_text = (
            f"Damage: {self.player.effective_damage}  Speed: {self.player.effective_speed}  "
            f"Defense: {self.player.defense}"
        )
        self.draw_text_with_shadow(
            stat_text,
            30,
            SCREEN_HEIGHT - 108,
            MUTED,
            self.fit_font_size(stat_text, 350, 11),
            350,
        )
        bar_left = 30
        bar_bottom = SCREEN_HEIGHT - 140
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
        if self.microplastics_effect_timer > 0:
            effect_y = bar_bottom + 26
            effect_title_size = self.fit_font_size(self.microplastics_effect_title, 320, 12)
            self.draw_text_with_shadow(self.microplastics_effect_title, bar_left, effect_y, arcade.color.GOLD, effect_title_size, 320)
            self.draw_wrapped_text(self.microplastics_effect_body, bar_left, effect_y - 16, TEXT, 10, 320)

        arcade.draw_lrbt_rectangle_filled(SCREEN_WIDTH - 250, SCREEN_WIDTH - 18, SCREEN_HEIGHT - 150, SCREEN_HEIGHT - 18, PANEL)
        self.draw_text_with_shadow("Objectives", SCREEN_WIDTH - 232, SCREEN_HEIGHT - 56, TEXT, 16)
        if self.state == "boss":
            objective = "Defeat the CEO"
        elif self.state == "inventory":
            objective = "Manage inventory"
        else:
            objective = "Clear the floor"
        self.draw_wrapped_text(objective, SCREEN_WIDTH - 232, SCREEN_HEIGHT - 72, MUTED, 13, 200)
        self.draw_text_with_shadow("Move: arrows or WASD", SCREEN_WIDTH - 232, SCREEN_HEIGHT - 108, MUTED, 11, 200)
        self.draw_wrapped_text("Attack: SPACE (aim with mouse)", SCREEN_WIDTH - 232, SCREEN_HEIGHT - 126, MUTED, 11, 200)
        weapon_style = self.player.equipped_weapon.weapon_style if self.player.equipped_weapon else ""
        ability_label = ""
        ability_cooldown = 0.0
        if weapon_style == "sweep":
            ability_label = "Q: Sweep"
            ability_cooldown = SWEEP_SPECIAL_COOLDOWN
        elif weapon_style == "lunge":
            ability_label = "E: Lunge"
            ability_cooldown = LUNGE_SPECIAL_COOLDOWN
        elif weapon_style == "pierce":
            ability_label = "R: Pierce"
            ability_cooldown = 1.15
        elif weapon_style == "slam":
            ability_label = "T: Slam"
            ability_cooldown = SLAM_SPECIAL_COOLDOWN
        elif weapon_style == "pulse":
            ability_label = "Y: Pulse"
            ability_cooldown = PULSE_SPECIAL_COOLDOWN
        else:
            ability_label = "Equip a special weapon"
        self.draw_text_with_shadow(ability_label, SCREEN_WIDTH - 232, SCREEN_HEIGHT - 144, MUTED, 11, 200)
        if self.player.equipped_weapon:
            if self.special_attack_timer > 0:
                self.draw_text_with_shadow(
                    f"Cooldown: {self.special_attack_timer:.1f}s / {ability_cooldown:.1f}s",
                    SCREEN_WIDTH - 232,
                    SCREEN_HEIGHT - 160,
                    arcade.color.ORANGE,
                    11,
                    200,
                )
            else:
                self.draw_text_with_shadow(
                    "Cooldown: ready",
                    SCREEN_WIDTH - 232,
                    SCREEN_HEIGHT - 160,
                    MUTED,
                    11,
                    200,
                )
        if self.state == "inventory":
            self.draw_wrapped_text("Click or press 1-9 to swap gear", SCREEN_WIDTH - 232, SCREEN_HEIGHT - 154, MUTED, 11, 200)
            self.draw_text_with_shadow("I or ENTER to close", SCREEN_WIDTH - 232, SCREEN_HEIGHT - 186, MUTED, 11, 200)

    def update_microplastics(self, delta_time: float) -> None:
        if self.state == "inventory":
            self.player.microplastics_tick = 0.0
            return
        previous_stage = self.player.microplastics_stage
        sustainability = self.player.sustainability
        if sustainability < 0:
            self.player.microplastics += ((-sustainability) ** 0.85) * MALAISE_GAIN_RATE * 0.4 * delta_time
        elif sustainability > 0:
            self.player.microplastics -= sustainability * MALAISE_RECOVERY_RATE * 0.75 * delta_time
        self.player.microplastics -= MALAISE_PASSIVE_RECOVERY * delta_time
        self.player.microplastics = max(0.0, min(MALAISE_MAX, self.player.microplastics))
        new_stage = self.player.microplastics_stage
        if new_stage != previous_stage:
            titles = ["Clean", "Dirty", "Toxic", "Critical"]
            bodies = [
                "Your gear is clean and the suit is calm.",
                "Microplastics are building up. Stay moving and swap better gear.",
                "The suit is starting to poison your flow.",
                "The build is overloaded. Clean up fast or get punished hard.",
            ]
            self.microplastics_effect_title = titles[new_stage]
            self.microplastics_effect_body = bodies[new_stage]
            self.microplastics_effect_timer = 4.2
            self._last_microplastics_stage = new_stage
        if self.microplastics_effect_timer > 0:
            self.microplastics_effect_timer -= delta_time

        if self.player.microplastics >= MALAISE_TICK_THRESHOLD:
            self.player.microplastics_tick += delta_time
            if self.player.microplastics_tick >= MALAISE_DAMAGE_INTERVAL:
                self.player.microplastics_tick = 0.0
                self.hit_player(MALAISE_TICK_DAMAGE)
        else:
            self.player.microplastics_tick = 0.0

    def update_enemies(self) -> None:
        for enemy in self.enemies[:]:
            if enemy.stun_timer > 0:
                enemy.stun_timer = max(0.0, enemy.stun_timer - self._last_delta_time)
                enemy.x += math.sin(enemy.stun_timer * 40.0) * 0.7
                enemy.y += math.cos(enemy.stun_timer * 36.0) * 0.7
            elif enemy.variant == "slime":
                enemy.ai_timer -= self._last_delta_time
                if enemy.ai_state == "idle":
                    if enemy.ai_timer <= 0:
                        enemy.ai_state = "leap"
                        enemy.ai_timer = 0.28
                elif enemy.ai_state == "leap":
                    dx = self.player.x - enemy.x
                    dy = self.player.y - enemy.y
                    dist = math.hypot(dx, dy) or 1.0
                    leap_speed = enemy.speed * 14.0
                    enemy.x += dx / dist * leap_speed
                    enemy.y += dy / dist * leap_speed
                    if enemy.ai_timer <= 0:
                        enemy.ai_state = "recover"
                        enemy.ai_timer = 1.0
                else:
                    if enemy.ai_timer <= 0:
                        enemy.ai_state = "idle"
                        enemy.ai_timer = random.uniform(0.9, 1.7)
            else:
                self.move_toward(enemy, self.player, enemy.speed)
            if enemy.variant == "zombie_orange" and random.random() < 0.015:
                self.enemy_projectiles.append(self.make_projectile_toward(enemy, self.player, 220, 6, arcade.color.ORANGE_RED))
            if self.rects_intersect(self.entity_hitbox(enemy, ENEMY_TOUCH_PADDING), self.entity_hitbox(self.player, 3)):
                self.hit_player(enemy.touch_damage)
            if enemy.health <= 0:
                self.enemies.remove(enemy)
                self.player.money += 5
                self.player.microplastics = max(0.0, self.player.microplastics - MALAISE_KILL_RECOVERY)
                self.current_message = "Enemy down. Microplastics dropped."

    def update_boss(self) -> None:
        self.move_toward(self.boss, self.player, self.boss.speed)
        if self.boss.variant == "robo":
            self.boss.projectile_cooldown -= self._last_delta_time
            if self.boss.projectile_cooldown <= 0:
                self.boss.projectile_cooldown = 1.1
                self.fire_boss_projectile()
        if self.rects_intersect(self.boss_hitbox(4), self.entity_hitbox(self.player, 3)):
            self.hit_player(self.boss.touch_damage)

    def fire_boss_projectile(self) -> None:
        dx = self.player.x - self.boss.x
        dy = self.player.y - self.boss.y
        dist = math.hypot(dx, dy) or 1.0
        self.boss_projectiles.append(
            Projectile(self.boss.x, self.boss.y, dx / dist, dy / dist, 240, 14, arcade.color.CYAN)
        )

    def make_projectile_toward(self, source: Entity, target: Entity, speed: float, damage: int, color: arcade.Color) -> Projectile:
        dx = target.x - source.x
        dy = target.y - source.y
        dist = math.hypot(dx, dy) or 1.0
        return Projectile(source.x, source.y, dx / dist, dy / dist, speed, damage, color)

    def update_projectiles(self, delta_time: float) -> None:
        for projectile_list in (self.enemy_projectiles, self.boss_projectiles):
            for projectile in projectile_list[:]:
                projectile.x += projectile.dx * projectile.speed * delta_time
                projectile.y += projectile.dy * projectile.speed * delta_time
                projectile.life -= delta_time
                if projectile.life <= 0:
                    projectile_list.remove(projectile)
                    continue
                if self.rects_intersect(self.entity_hitbox(projectile, 0), self.entity_hitbox(self.player, 2)):
                    self.hit_player(projectile.damage)
                    if projectile in projectile_list:
                        projectile_list.remove(projectile)


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
        bonus_reduction = 2 if self.player.legendary_armor_ability == "winter" else 0
        damage = max(1, incoming - self.player.defense - bonus_reduction + malaise_penalty)
        self.player.health -= damage
        # Enemy contact should build microplastics gradually so it feels like a long-term pressure.
        microplastics_gain = max(MALAISE_HIT_MINIMUM, damage * MALAISE_HIT_MULTIPLIER)
        self.player.microplastics = min(MALAISE_MAX, self.player.microplastics + microplastics_gain)
        self.player.invuln_timer = 0.6
        self.damage_flash = 0.18
        # smaller, controlled damage indicator (no giant red circle)
        self.current_message = f"You took {damage} damage."
        if self.player.health <= 0:
            self.state = "game_over"
            self.current_message = "The movement stalled. Press R to retry."

    def equip_from_inventory(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.player.inventory):
            return
        item = self.player.inventory[idx]
        if item.type == "weapon":
            # swap
            if self.player.equipped_weapon:
                self.player.inventory.append(self.player.equipped_weapon)
            self.player.equipped_weapon = item
            self.player.inventory.pop(idx)
            self.current_message = f"Equipped {item.name} as weapon."
        elif item.type == "armor":
            if self.player.equipped_armor:
                self.player.inventory.append(self.player.equipped_armor)
            self.player.equipped_armor = item
            self.player.inventory.pop(idx)
            self.current_message = f"Equipped {item.name} as armor."
        self.player.refresh_stats()
        self.player.update_visual_theme_from_equipment()

    def clear_drag_state(self) -> None:
        self.dragged_item_index = None
        self.dragged_item_source = ""
        self.dragged_item_offset_x = 0.0
        self.dragged_item_offset_y = 0.0
        self.dragged_item_label = ""
        self.dragged_from_equipment = None
        self.inventory_dragging = False
        self.dragged_from_inventory_index = None
        self.hovered_inventory_index = None

    def begin_drag_inventory(self, idx: int, x: float, y: float) -> None:
        self.dragged_item_index = idx
        self.dragged_item_source = "inventory"
        self.dragged_from_inventory_index = idx
        self.inventory_dragging = True
        left, right, bottom, top = self.inv_bounds[idx]
        self.dragged_item_offset_x = x - (left + right) / 2
        self.dragged_item_offset_y = y - (bottom + top) / 2
        self.dragged_item_label = self.player.inventory[idx].name
        self.dragged_from_equipment = None

    def begin_drag_equipped(self, slot_name: str, x: float, y: float) -> None:
        item = self.player.equipped_weapon if slot_name == "weapon" else self.player.equipped_armor
        if item is None:
            return
        self.dragged_item_source = "equipment"
        self.dragged_from_equipment = slot_name
        self.inventory_dragging = True
        bounds = self.equipment_slots[slot_name]
        left, right, bottom, top = bounds
        self.dragged_item_offset_x = x - (left + right) / 2
        self.dragged_item_offset_y = y - (bottom + top) / 2
        self.dragged_item_label = item.name

    def finish_drag(self, x: float, y: float) -> None:
        if self.dragged_item_source == "inventory" and self.dragged_item_index is not None:
            item = self.player.inventory[self.dragged_item_index]
            slot = self.drop_slot_for_position(x, y)
            if slot == "weapon" and item.type == "weapon":
                self.equip_item_to_slot(self.dragged_item_index, "weapon")
            elif slot == "armor" and item.type == "armor":
                self.equip_item_to_slot(self.dragged_item_index, "armor")
            elif slot == "trash":
                removed = self.player.inventory.pop(self.dragged_item_index)
                self.current_message = f"Trashed {removed.name}."
            else:
                inv_target = self.inventory_slot_for_position(x, y)
                if inv_target is not None and inv_target != self.dragged_item_index:
                    self.player.inventory[self.dragged_item_index], self.player.inventory[inv_target] = (
                        self.player.inventory[inv_target],
                        self.player.inventory[self.dragged_item_index],
                    )
                    self.current_message = f"Moved {item.name} in inventory."
                else:
                    self.current_message = f"Drop {item.name} on a matching slot."
        elif self.dragged_item_source == "equipment" and self.dragged_from_equipment:
            item = self.player.equipped_weapon if self.dragged_from_equipment == "weapon" else self.player.equipped_armor
            if item:
                slot = self.drop_slot_for_position(x, y)
                if slot == "trash":
                    if self.dragged_from_equipment == "weapon":
                        self.player.equipped_weapon = None
                    else:
                        self.player.equipped_armor = None
                    self.current_message = f"Trashed {item.name}."
                    self.player.refresh_stats()
                elif slot is None:
                    if self.dragged_from_equipment == "weapon":
                        self.player.inventory.append(item)
                        self.player.equipped_weapon = None
                    else:
                        self.player.inventory.append(item)
                        self.player.equipped_armor = None
                    self.player.refresh_stats()
                    self.current_message = f"Unequipped {item.name}."
                elif slot != self.dragged_from_equipment:
                    self.move_equipped_item_between_slots(self.dragged_from_equipment, slot)
        self.clear_drag_state()

    def drop_slot_for_position(self, x: float, y: float) -> Optional[str]:
        for slot_name, bounds in self.equipment_slots.items():
            left, right, bottom, top = bounds
            if left <= x <= right and bottom <= y <= top:
                return slot_name
        if self.trash_slot:
            left, right, bottom, top = self.trash_slot
            if left <= x <= right and bottom <= y <= top:
                return "trash"
        return None

    def inventory_slot_for_position(self, x: float, y: float) -> Optional[int]:
        for idx, bounds in enumerate(self.inv_bounds):
            left, right, bottom, top = bounds
            if left <= x <= right and bottom <= y <= top and idx < len(self.player.inventory):
                return idx
        return None

    def equip_item_to_slot(self, idx: int, slot_name: str) -> None:
        if idx < 0 or idx >= len(self.player.inventory):
            return
        item = self.player.inventory.pop(idx)
        if slot_name == "weapon":
            if self.player.equipped_weapon:
                self.player.inventory.append(self.player.equipped_weapon)
            self.player.equipped_weapon = item
            self.current_message = f"Equipped {item.name} as weapon."
        else:
            if self.player.equipped_armor:
                self.player.inventory.append(self.player.equipped_armor)
            self.player.equipped_armor = item
            self.current_message = f"Equipped {item.name} as armor."
        self.player.refresh_stats()
        self.player.update_visual_theme_from_equipment()

    def move_equipped_item_between_slots(self, from_slot: str, to_slot: str) -> None:
        source_item = self.player.equipped_weapon if from_slot == "weapon" else self.player.equipped_armor
        if source_item is None:
            return
        target_item = self.player.equipped_weapon if to_slot == "weapon" else self.player.equipped_armor
        if from_slot == "weapon":
            self.player.equipped_weapon = target_item
        else:
            self.player.equipped_armor = target_item
        if to_slot == "weapon":
            self.player.equipped_weapon = source_item
        else:
            self.player.equipped_armor = source_item
        self.current_message = f"Moved {source_item.name} to {to_slot}."
        self.player.refresh_stats()
        self.player.update_visual_theme_from_equipment()

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
            self.draw_center_panel(
                "INTO THE FASHEON by hunter and ollin",
                "Use arrow keys or WASD to move. Click to aim. Press SPACE to attack. Different weapons can unlock special abilities, and the keybinds in the top right show how to use them. The more microplastics you build up, the stronger the negative effects become. Press ENTER to start.",
            )
        elif self.state == "game_over":
            self.draw_center_panel("Game Over", "Press R to restart.")
        elif self.state == "inventory":
            self.draw_inventory_menu()
            self.draw_inventory_tooltip()

    def draw_building(self, shake_x: int, shake_y: int) -> None:
        left = 0 + shake_x
        right = SCREEN_WIDTH + shake_x
        bottom = 0 + shake_y
        top = SCREEN_HEIGHT + shake_y
        if self.floor_texture:
            rect = arcade.Rect(
                left,
                right,
                bottom,
                top,
                SCREEN_WIDTH,
                SCREEN_HEIGHT,
                SCREEN_WIDTH / 2 + shake_x,
                SCREEN_HEIGHT / 2 + shake_y,
            )
            draw_texture = getattr(arcade, "draw_texture_rect", None)
            draw_scaled_texture = getattr(arcade, "draw_scaled_texture_rectangle", None)
            if draw_texture is not None:
                try:
                    draw_texture(self.floor_texture, rect)
                except TypeError:
                    try:
                        draw_texture(self.floor_texture, rect)
                    except TypeError:
                        if draw_scaled_texture is not None:
                            draw_scaled_texture(
                                SCREEN_WIDTH / 2 + shake_x,
                                SCREEN_HEIGHT / 2 + shake_y,
                                self.floor_texture,
                                SCREEN_WIDTH,
                                SCREEN_HEIGHT,
                                90,
                            )
                        else:
                            draw_texture(rect, self.floor_texture)
            else:
                if draw_scaled_texture is not None:
                    draw_scaled_texture(
                        SCREEN_WIDTH / 2 + shake_x,
                        SCREEN_HEIGHT / 2 + shake_y,
                        self.floor_texture,
                        SCREEN_WIDTH,
                        SCREEN_HEIGHT,
                        90,
                    )
                else:
                    arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, arcade.color.DARK_BROWN)
            overlay = (0, 0, 0, 35)
            arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, overlay)
        else:
            arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, arcade.color.DARK_BROWN)

    def draw_background(self) -> None:
        for i, y in enumerate((40, 120, 200, 280, 360, 440, 520, 600)):
            color = arcade.color.DARK_SLATE_GRAY if i % 2 == 0 else arcade.color.DARK_SLATE_BLUE
            arcade.draw_arc_filled(SCREEN_WIDTH / 2, y, SCREEN_WIDTH + 260, 180, color, 0, 180)
        arcade.draw_circle_filled(110, SCREEN_HEIGHT - 110, 48, arcade.color.DARK_GOLDENROD)
        arcade.draw_circle_filled(SCREEN_WIDTH - 110, SCREEN_HEIGHT - 140, 26, arcade.color.LIGHT_GRAY)
        for x in range(80, SCREEN_WIDTH, 140):
            arcade.draw_line(x, 0, x + 60, 0, arcade.color.BLACK_OLIVE, 4)
            arcade.draw_line(x, 0, x + 28, 18, arcade.color.DARK_OLIVE_GREEN, 2)

    def draw_entities(self, shake_x: int, shake_y: int) -> None:
        self.draw_player(shake_x, shake_y)
        for enemy in self.enemies:
            self.draw_enemy(enemy, shake_x, shake_y)
        self.draw_projectiles(shake_x, shake_y)
        if self.state == "boss":
            self.draw_boss(shake_x, shake_y)
        if self.punch_timer > 0:
            self.draw_punch(shake_x, shake_y)
        if self.special_attack_effect_timer > 0:
            self.draw_special_attack_effect(shake_x, shake_y)

    def draw_projectiles(self, shake_x: int, shake_y: int) -> None:
        for projectile in self.enemy_projectiles + self.boss_projectiles:
            arcade.draw_circle_filled(projectile.x + shake_x, projectile.y + shake_y, 6, projectile.color)
            arcade.draw_circle_outline(projectile.x + shake_x, projectile.y + shake_y, 6, arcade.color.BLACK, 1)
    def draw_punch(self, shake_x: int, shake_y: int) -> None:
        progress = 1.0 - max(0.0, self.punch_timer) / PUNCH_ANIMATION_TIME
        reach = 18 + progress * 38
        if self.player.facing_x != 0 and self.player.facing_y != 0:
            start_x = self.player.x + (self.player.width / 2) * self.player.facing_x + shake_x
            start_y = self.player.y + (self.player.height / 2) * self.player.facing_y + shake_y
            punch_x = self.player.x + (self.player.width / 2) * self.player.facing_x + reach * self.player.facing_x + shake_x
            punch_y = self.player.y + (self.player.height / 2) * self.player.facing_y + reach * self.player.facing_y + shake_y
        elif self.player.facing_x > 0:
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
            # visualize arc in direction of mouse/facing
            aim_x = self.mouse_x - self.player.x
            aim_y = self.mouse_y - self.player.y
            if abs(aim_x) < 1e-3 and abs(aim_y) < 1e-3:
                aim_x = self.player.facing_x
                aim_y = self.player.facing_y
            angle = math.degrees(math.atan2(aim_y, aim_x))
            arcade.draw_arc_outline(
                self.player.x + shake_x,
                self.player.y + shake_y,
                300,
                300,
                arcade.color.MEDIUM_AQUAMARINE,
                angle - 60,
                angle + 60,
                8,
                6,
            )
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
        elif self.special_attack_effect == "pierce":
            end_x = self.player.x + self.player.facing_x * 180 + shake_x
            end_y = self.player.y + self.player.facing_y * 180 + shake_y
            arcade.draw_line(self.player.x + shake_x, self.player.y + shake_y, end_x, end_y, arcade.color.CYAN, 8)
        elif self.special_attack_effect == "slam":
            arcade.draw_circle_outline(self.player.x + shake_x, self.player.y + shake_y, 78, arcade.color.ORANGE, 5)
        elif self.special_attack_effect == "pulse":
            arcade.draw_circle_outline(self.player.x + shake_x, self.player.y + shake_y, 112, arcade.color.TURQUOISE, 4)

    def draw_health_bar(self, entity: Entity, shake_x: int, shake_y: int, bar_color: arcade.Color = arcade.color.LIME_GREEN) -> None:
        health_ratio = max(0, entity.health) / entity.max_health
        left = entity.x - entity.width / 2 + shake_x
        bottom = entity.y + entity.height / 2 + 16 + shake_y
        arcade.draw_lbwh_rectangle_filled(left, bottom, entity.width, 6, arcade.color.DARK_RED)
        arcade.draw_lbwh_rectangle_filled(left, bottom, entity.width * health_ratio, 6, bar_color)

    def draw_player(self, shake_x: int, shake_y: int) -> None:
        x = self.player.x + shake_x
        y = self.player.y + shake_y
        texture = self.player_textures.get(self.player.visual_theme) or self.player_textures.get("default")
        if texture is not None:
            draw_rect = getattr(arcade, "draw_texture_rect", None)
            if draw_rect is not None:
                tex_width = self.player.width * 2.4
                tex_height = self.player.height * 2.4
                rect = arcade.Rect(
                    x - tex_width / 2,
                    x + tex_width / 2,
                    y - tex_height / 2,
                    y + tex_height / 2,
                    tex_width,
                    tex_height,
                    x,
                    y,
                )
                try:
                    draw_rect(texture, rect)
                except TypeError:
                    draw_rect(rect, texture)
            else:
                body_color = arcade.color.AQUA if self.player.microplastics_stage == 0 else arcade.color.TURQUOISE
                arcade.draw_ellipse_filled(x, y, self.player.width + 6, self.player.height + 4, arcade.color.BLACK_OLIVE)
                arcade.draw_lbwh_rectangle_filled(x - self.player.width / 2, y - self.player.height / 2, self.player.width, self.player.height, body_color)
                arcade.draw_triangle_filled(x, y + 10, x - 18, y + 24, x + 18, y + 24, arcade.color.LIGHT_GRAY)
                arcade.draw_circle_filled(x - 8, y + 14, 3, arcade.color.BLACK)
                arcade.draw_circle_filled(x + 8, y + 14, 3, arcade.color.BLACK)
                if self.player.facing_x != 0 or self.player.facing_y != 0:
                    fx = self.player.facing_x
                    fy = self.player.facing_y
                    arcade.draw_line(x, y + 4, x + fx * 22, y + 4 + fy * 22, arcade.color.WHITE, 3)
        else:
            body_color = arcade.color.AQUA if self.player.microplastics_stage == 0 else arcade.color.TURQUOISE
            arcade.draw_ellipse_filled(x, y, self.player.width + 6, self.player.height + 4, arcade.color.BLACK_OLIVE)
            arcade.draw_lbwh_rectangle_filled(x - self.player.width / 2, y - self.player.height / 2, self.player.width, self.player.height, body_color)
            arcade.draw_triangle_filled(x, y + 10, x - 18, y + 24, x + 18, y + 24, arcade.color.LIGHT_GRAY)
            arcade.draw_circle_filled(x - 8, y + 14, 3, arcade.color.BLACK)
            arcade.draw_circle_filled(x + 8, y + 14, 3, arcade.color.BLACK)
            if self.player.facing_x != 0 or self.player.facing_y != 0:
                fx = self.player.facing_x
                fy = self.player.facing_y
                arcade.draw_line(x, y + 4, x + fx * 22, y + 4 + fy * 22, arcade.color.WHITE, 3)
        if self.player.microplastics_stage > 0:
            glow = 2 + self.player.microplastics_stage
            arcade.draw_circle_outline(x, y, 28 + self.player.microplastics_stage * 3, arcade.color.ORANGE_RED, glow)
            if self.player.microplastics_stage >= 2:
                arcade.draw_circle_outline(x, y, 36 + self.player.microplastics_stage * 2, arcade.color.ORANGE, 1)
        # draw equipped items icons
        if self.player.equipped_weapon:
            arcade.draw_circle_filled(x - 20, y - 22, 6, self.player.equipped_weapon.color)
        if self.player.equipped_armor:
            arcade.draw_circle_filled(x + 20, y - 22, 6, self.player.equipped_armor.color)
        self.draw_health_bar(self.player, shake_x, shake_y, arcade.color.AQUA)

    def draw_enemy(self, entity: Enemy, shake_x: int, shake_y: int) -> None:
        x = entity.x + shake_x
        y = entity.y + shake_y
        if entity.stun_timer > 0:
            x += math.sin(entity.stun_timer * 40.0) * 2.0
            y += math.cos(entity.stun_timer * 36.0) * 2.0
        texture = self.enemy_textures.get(getattr(entity, "variant", ""))
        if texture is not None and hasattr(arcade, "draw_texture_rect"):
            rect = arcade.Rect(
                x - entity.width,
                x + entity.width,
                y - entity.height,
                y + entity.height,
                entity.width * 2,
                entity.height * 2,
                x,
                y,
            )
            try:
                arcade.draw_texture_rect(texture, rect)
            except TypeError:
                arcade.draw_texture_rect(rect, texture)
        else:
            arcade.draw_circle_filled(x, y, entity.width * 0.58, arcade.color.BLACK_OLIVE)
            arcade.draw_lbwh_rectangle_filled(x - entity.width / 2, y - entity.height / 2, entity.width, entity.height, entity.color)
            arcade.draw_triangle_filled(x - 6, y + 10, x - 18, y + 22, x + 2, y + 18, arcade.color.GOLD)
            arcade.draw_triangle_filled(x + 6, y + 10, x + 18, y + 22, x - 2, y + 18, arcade.color.GOLD)
            arcade.draw_circle_filled(x - 7, y + 2, 3, arcade.color.WHITE)
            arcade.draw_circle_filled(x + 7, y + 2, 3, arcade.color.WHITE)
            arcade.draw_line(x - 8, y - 11, x + 8, y - 11, arcade.color.BLACK, 2)
        self.draw_health_bar(entity, shake_x, shake_y)

    def draw_boss(self, shake_x: int, shake_y: int) -> None:
        x = self.boss.x + shake_x
        y = self.boss.y + shake_y
        texture = self.boss_textures.get(getattr(self.boss, "variant", ""))
        if texture is not None and hasattr(arcade, "draw_texture_rect"):
            rect = arcade.Rect(
                x - self.boss.width,
                x + self.boss.width,
                y - self.boss.height,
                y + self.boss.height,
                self.boss.width * 2.1,
                self.boss.height * 2.1,
                x,
                y,
            )
            try:
                arcade.draw_texture_rect(texture, rect)
            except TypeError:
                arcade.draw_texture_rect(rect, texture)
        else:
            arcade.draw_circle_filled(x, y, 66, arcade.color.BLACK_OLIVE)
            arcade.draw_lbwh_rectangle_filled(x - self.boss.width / 2, y - self.boss.height / 2, self.boss.width, self.boss.height, arcade.color.PURPLE)
            arcade.draw_lbwh_rectangle_filled(x - 36, y - 43, 72, 74, arcade.color.DARK_SLATE_BLUE)
            arcade.draw_triangle_filled(x, y + 36, x - 30, y + 10, x + 30, y + 10, arcade.color.GOLD)
            arcade.draw_circle_filled(x - 18, y + 14, 5, arcade.color.WHITE)
            arcade.draw_circle_filled(x + 18, y + 14, 5, arcade.color.WHITE)
            arcade.draw_line(x - 16, y - 18, x + 16, y - 18, arcade.color.BLACK, 3)
        self.draw_health_bar(self.boss, shake_x, shake_y, arcade.color.ORANGE)

    def draw_messages(self) -> None:
        message_size = self.fit_font_size(self.current_message, SCREEN_WIDTH - 40, 14)
        self.draw_text_with_shadow(self.current_message, SCREEN_WIDTH / 2, 18, arcade.color.GOLD, message_size, SCREEN_WIDTH - 40, anchor_x="center", align="center")

    def draw_center_panel(self, title: str, subtitle: str) -> None:
        panel_left = SCREEN_WIDTH / 2 - 300
        panel_bottom = SCREEN_HEIGHT / 2 - 130
        arcade.draw_lbwh_rectangle_filled(panel_left, panel_bottom, 600, 260, arcade.color.BLACK_OLIVE)
        arcade.draw_lbwh_rectangle_outline(panel_left, panel_bottom, 600, 260, arcade.color.WHITE, 3)
        self.draw_text_with_shadow(title, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 58, TEXT, 28, anchor_x="center")
        self.draw_wrapped_text(subtitle, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 24, MUTED, 14, 520, anchor_x="center", align="center")

    def draw_inventory_menu(self) -> None:
        panel_left = SCREEN_WIDTH / 2 - 390
        panel_bottom = SCREEN_HEIGHT / 2 - 180
        panel_width = 780
        panel_height = 360
        arcade.draw_lbwh_rectangle_filled(panel_left, panel_bottom, panel_width, panel_height, arcade.color.DARK_BLUE_GRAY)
        arcade.draw_lbwh_rectangle_outline(panel_left, panel_bottom, panel_width, panel_height, arcade.color.WHITE, 3)
        self.draw_text_with_shadow("Inventory", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 146, TEXT, 26, anchor_x="center")
        self.inv_bounds = []
        self.inventory_slots = []
        self.equipment_slots = {}
        self.trash_slot = None
        eq_left = panel_left + 24
        eq_top = panel_bottom + panel_height - 44
        self.draw_text_with_shadow("Equipped", eq_left, eq_top, MUTED, 12)
        ew = self.player.equipped_weapon
        ea = self.player.equipped_armor
        weapon_slot = (eq_left, eq_left + 290, eq_top - 46, eq_top - 2)
        armor_slot = (eq_left, eq_left + 290, eq_top - 144, eq_top - 100)
        trash_slot = (eq_left, eq_left + 290, eq_top - 254, eq_top - 210)
        self.equipment_slots["weapon"] = weapon_slot
        self.equipment_slots["armor"] = armor_slot
        self.trash_slot = trash_slot
        for slot_name, bounds in self.equipment_slots.items():
            left, right, bottom, top = bounds
            highlight = arcade.color.YELLOW if self.is_point_in_drag_hover(left, right, bottom, top) else arcade.color.GOLD
            arcade.draw_lbwh_rectangle_outline(left, bottom, right - left, top - bottom, highlight, 2)
        trash_left, trash_right, trash_bottom, trash_top = trash_slot
        trash_highlight = arcade.color.RED if self.is_point_in_drag_hover(trash_left, trash_right, trash_bottom, trash_top) else arcade.color.DARK_RED
        arcade.draw_lbwh_rectangle_outline(trash_left, trash_bottom, trash_right - trash_left, trash_top - trash_bottom, trash_highlight, 2)
        self.draw_text_with_shadow("W", weapon_slot[0] + 274, weapon_slot[2] + 11, arcade.color.CYAN, 16, anchor_x="center")
        self.draw_text_with_shadow("Drag weapon here", weapon_slot[0] + 10, weapon_slot[2] + 30, MUTED, 8)
        if ew:
            self.draw_fitted_text(self.compact_label(ew.name, 26), weapon_slot[0] + 10, weapon_slot[2] + 10, arcade.color.WHITE, 228, 11, 8)
        else:
            self.draw_text_with_shadow("Empty", weapon_slot[0] + 10, weapon_slot[2] + 2, arcade.color.GRAY, 10)
        self.draw_text_with_shadow("A", armor_slot[0] + 274, armor_slot[2] + 11, arcade.color.ORANGE, 16, anchor_x="center")
        self.draw_text_with_shadow("Drag armor here", armor_slot[0] + 10, armor_slot[2] + 30, MUTED, 8)
        if ea:
            self.draw_fitted_text(self.compact_label(ea.name, 26), armor_slot[0] + 10, armor_slot[2] + 10, arcade.color.WHITE, 228, 11, 8)
        else:
            self.draw_text_with_shadow("Empty", armor_slot[0] + 10, armor_slot[2] + 2, arcade.color.GRAY, 10)
        self.draw_text_with_shadow("Trash slot", trash_left + 10, trash_top - 18, arcade.color.RED, 11)
        self.draw_text_with_shadow("Drop unwanted items here", trash_left + 10, trash_top - 34, MUTED, 8)
        self.draw_text_with_shadow("TRASH", trash_left + 272, trash_bottom + 11, arcade.color.RED, 14, anchor_x="center")

        grid_left = panel_left + 330
        grid_top = panel_bottom + panel_height - 48
        cols = 3
        rows = 4
        grid_right = panel_left + panel_width - 24
        grid_bottom = panel_bottom + 20
        grid_width = grid_right - grid_left
        grid_height = grid_top - grid_bottom
        cell_gap_x = 10
        cell_gap_y = 20
        cell_size = min(
            (grid_width - (cols - 1) * cell_gap_x) / cols,
            (grid_height - (rows - 1) * cell_gap_y) / rows,
        )
        for slot_idx in range(cols * rows):
            row = slot_idx // cols
            col = slot_idx % cols
            left = grid_left + col * (cell_size + cell_gap_x)
            top = grid_top - row * (cell_size + cell_gap_y)
            bottom = top - cell_size
            right = left + cell_size
            self.inv_bounds.append((left, right, bottom, top))
            self.inventory_slots.append((left, right, bottom, top))
            arcade.draw_lbwh_rectangle_filled(left, bottom, cell_size, cell_size, arcade.color.DARK_GRAY)
            arcade.draw_lbwh_rectangle_outline(left, bottom, cell_size, cell_size, arcade.color.WHITE, 2)
            if slot_idx < len(self.player.inventory):
                item = self.player.inventory[slot_idx]
                center_x = (left + right) / 2
                center_y = bottom + cell_size * 0.68
                arcade.draw_circle_filled(center_x, center_y, 16, item.color)
                name_width = cell_size - 24
                name_size = self.fit_font_size(item.name, name_width, 9, 7)
                self.draw_fitted_text(self.compact_label(item.name, 20), left + 12, bottom + cell_size * 0.32, TEXT, name_width, name_size, 7)
                self.draw_text_with_shadow(str(slot_idx + 1), right - 13, bottom + 10, arcade.color.WHITE, 8, anchor_x="center")
        if len(self.player.inventory) > cols * rows:
            self.draw_text_with_shadow("Inventory full, extra drops are hidden.", grid_left, panel_bottom + 14, arcade.color.GOLD, 10)
        if self.inventory_dragging and self.dragged_item_label:
            drag_x = self.dragged_item_mouse_x - self.dragged_item_offset_x
            drag_y = self.dragged_item_mouse_y - self.dragged_item_offset_y
            active_item = None
            if self.dragged_item_source == "inventory" and self.dragged_item_index is not None and self.dragged_item_index < len(self.player.inventory):
                active_item = self.player.inventory[self.dragged_item_index]
            elif self.dragged_item_source == "equipment" and self.dragged_from_equipment:
                active_item = self.player.equipped_weapon if self.dragged_from_equipment == "weapon" else self.player.equipped_armor
            fill = active_item.color if active_item else arcade.color.WHITE
            arcade.draw_lbwh_rectangle_filled(drag_x - 250, drag_y - 16, 500, 32, fill)
            arcade.draw_lbwh_rectangle_outline(drag_x - 250, drag_y - 16, 500, 32, arcade.color.BLACK, 2)
            label = self.compact_label(self.dragged_item_label, 30)
            if active_item:
                label = f"{active_item.type_label} | {label}"
            self.draw_wrapped_text(label, drag_x - 234, drag_y - 4, arcade.color.BLACK, 10, 450)

    def draw_inventory_tooltip(self) -> None:
        if self.state != "inventory":
            return
        item = self.hovered_inventory_item()
        if item is None:
            return

        width = 290
        padding = 10
        body_width = width - padding * 2
        title_size = 15
        body_size = 11
        line_gap = 8
        summary_lines = max(1, math.ceil(len(item.summary) / max(1, int(body_width / max(1, body_size * 0.58))))) if item.summary else 1
        desc_text = item.description or "No description."
        desc_lines = max(1, math.ceil(len(desc_text) / max(1, int(body_width / max(1, body_size * 0.58)))))
        total_height = 18 + title_size + 14 + body_size + line_gap + summary_lines * (body_size + 2) + 8 + desc_lines * (body_size + 2)

        x = self.mouse_x + 18
        y = self.mouse_y + 18
        if x + width > SCREEN_WIDTH - 12:
            x = self.mouse_x - width - 18
        if y + total_height > SCREEN_HEIGHT - 12:
            y = self.mouse_y - total_height - 18
        x = max(12, x)
        y = max(12, y)

        arcade.draw_lrbt_rectangle_filled(x, x + width, y, y + total_height, arcade.color.BLACK_OLIVE)
        arcade.draw_lrbt_rectangle_outline(x, x + width, y, y + total_height, arcade.color.WHITE, 2)
        self.draw_text_with_shadow(item.name, x + padding, y + total_height - padding - title_size, TEXT, title_size, body_width)
        current_y = y + total_height - padding - title_size - 14
        self.draw_text_with_shadow(item.type_label, x + padding, current_y, item.type_color, 11, body_width)
        current_y -= body_size + line_gap
        self.draw_wrapped_text(item.summary, x + padding, current_y, MUTED, body_size, body_width)
        current_y -= max(body_size + 20, summary_lines * (body_size + 2) + 8)
        self.draw_wrapped_text(item.description or "No description.", x + padding, current_y, TEXT, body_size, body_width)

    def is_point_in_drag_hover(self, left: float, right: float, bottom: float, top: float) -> bool:
        if not self.inventory_dragging:
            return False
        x = self.dragged_item_mouse_x
        y = self.dragged_item_mouse_y
        return left <= x <= right and bottom <= y <= top

    def point_in_rect(self, x: float, y: float, bounds: tuple[float, float, float, float]) -> bool:
        left, right, bottom, top = bounds
        return left <= x <= right and bottom <= y <= top

    def hovered_inventory_item(self) -> Optional[Item]:
        if self.state != "inventory":
            return None
        idx = self.hovered_inventory_index
        if idx is not None and idx < len(self.player.inventory):
            return self.player.inventory[idx]
        x = self.mouse_x
        y = self.mouse_y
        if self.player.equipped_weapon and self.point_in_rect(x, y, self.equipment_slots.get("weapon", (0, 0, 0, 0))):
            return self.player.equipped_weapon
        if self.player.equipped_armor and self.point_in_rect(x, y, self.equipment_slots.get("armor", (0, 0, 0, 0))):
            return self.player.equipped_armor
        return None

def main() -> None:
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    view = GameView()
    window.show_view(view)
    arcade.run()


if __name__ == "__main__":
    main()
                                      
