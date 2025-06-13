import random
import pygame

# Base entity with position and sprite
class GameEntity:
    def __init__(self, sprite, x, y):
        self.sprite = sprite
        self.x = x
        self.y = y


class MonsterEntity(GameEntity):
    def __init__(self, monster, sprite, x, y, is_miniboss=False):
        super().__init__(sprite, x, y)
        self.monster = monster
        self.is_miniboss = is_miniboss


class LootItem(GameEntity):
    def __init__(self, item_type, sprite, x, y):
        super().__init__(sprite, x, y)
        self.item_type = item_type


class Monster:
    def __init__(self, level, stats):
        self.level = level
        self.health = 100 * level
        self.max_health = self.health
        self.damage = 10 * level
        self.stats = stats
        self.is_alive = True
        self.last_attack_time = 0

        self.wander_direction_x = random.choice([-1, 0, 1])
        self.wander_direction_y = random.choice([-1, 0, 1])
        self.direction_change_timer = 0

        self.parse_stats(stats)

    def parse_stats(self, stats):
        try:
            lines = stats.split("\n")
            for line in lines:
                if "Health" in line:
                    health = int(line.split(":")[1].strip())
                    self.health = max(100 * self.level, health)
                    self.max_health = self.health
                elif "Damage" in line:
                    self.damage = int(line.split(":")[1].strip())
        except Exception:
            self.health = 100 * self.level
            self.max_health = self.health
            self.damage = 10 * self.level

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.is_alive = False

    def get_health_ratio(self):
        return self.health / self.max_health


class Player:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.health = 100
        self.level = 1
        self.inventory = []
        self.attack_power = 10
        self.attack_range = 32 * 2.5
        self.last_attack_time = 0
        self.sprite = None

    def get_max_health(self):
        armor_count = len([i for i in self.inventory if i.item_type == "armor"])
        return 100 + (armor_count * 25)
