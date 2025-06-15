"""Game constants and configuration values."""

# Window and display constants
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
TILE_SIZE = 32

# Level generation constants
INITIAL_MONSTER_COUNT = 3
MONSTER_INCREMENT = 2
MAX_MONSTER_COUNT = 50

# Game balance constants
PLAYER_BASE_HEALTH = 5
PLAYER_BASE_ATTACK = 0.5
PLAYER_SPEED = 5
MONSTER_HEALTH_MULTIPLIER = 1  # Monster HP = level * multiplier
MONSTER_DAMAGE_MULTIPLIER = 1  # Monster damage = level * multiplier

# Visual constants
HEALTH_BAR_WIDTH = 32
HEALTH_BAR_HEIGHT = 4

# Loot constants
LOOT_DROP_CHANCE = 0.3

# Combat timing constants (in milliseconds)
PLAYER_ATTACK_COOLDOWN = 500  # 0.5 seconds
MONSTER_ATTACK_COOLDOWN = 1000  # 1 second

# Monster AI constants
MONSTER_AGGRESSIVE_DISTANCE = 150  # Pixels - monsters always chase within this range
MONSTER_ALERT_DISTANCE = 300  # Pixels - monsters sometimes chase within this range
MONSTER_ALERT_CHASE_CHANCE = 0.7  # 70% chance to chase when in alert zone
MONSTER_WANDER_SPEED = 0.5  # Slower movement for wandering monsters
MONSTER_DIRECTION_CHANGE_CHANCE = 0.02  # 2% chance per frame to change direction
MONSTER_ATTACK_RANGE = TILE_SIZE  # Monsters need to be adjacent to attack (melee only)

# Mini-boss clustering constants
MINIBOSS_INFLUENCE_RADIUS = 200  # Pixels - monsters within this range are influenced by mini-boss
MINIBOSS_BIAS_CHANCE = 0.3  # 30% chance to move toward mini-boss when in range (similar to alert zone)

# Monster dispersion constants
MONSTER_DISPERSION_RADIUS = 80  # Pixels - monsters within this range trigger dispersion
MONSTER_DISPERSION_CHANCE = 0.5  # 50% chance to apply dispersion when clustered

# Death sprite constants
DEATH_SPRITE_LIFETIME = 90  # Frames - 1.5 seconds at 60 FPS
DEATH_SPRITE_MINIBOSS_LIFETIME = 180  # Frames - 3 seconds for mini-bosses
DEATH_SPRITE_MINIBOSS_SCALE = 1.5  # Scale factor for mini-boss death sprites
STAIRWAY_SCALE = 2.0  # Scale factor for stairway sprites

# Colors
BACKGROUND_COLOR = (32, 32, 48)  # Dark blue-gray
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 100)
CYAN = (0, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
GOLD = (255, 215, 0)

# Cache directories
CACHE_SPRITES_DIR = 'cache/sprites'
CACHE_MONSTERS_DIR = 'cache/monsters'
CACHE_ITEMS_DIR = 'cache/items'