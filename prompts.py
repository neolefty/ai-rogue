# Prompt constants for AI generation

PLAYER_SPRITE_PROMPT = "Create a fantasy hero sprite"
MONSTER_SPRITE_PROMPT = "Create a fantasy monster sprite for level {level}"
ITEM_SPRITE_PROMPT = "Create a fantasy {item_type} sprite"
STAIRWAY_SPRITE_PROMPT = "Create a stone stairway going down sprite"

SPRITE_STYLE = (
    "Style: 16x16 retro pixel art sprite with minimal shapes, drawn with light colors on a dark background. "
    "Background must be solid pure black (#000000) with no gradients, no scenery, "
    "no frames, and no captions."
)

MONSTER_STATS_SYSTEM_PROMPT = "You are a dungeon monster generator."
MONSTER_STATS_USER_PROMPT = "Generate stats for a level {level} monster."

DUNGEON_MONSTER_DESCRIPTION_PROMPT = (
    "Generate a unique monster name and description for level {level}"
)
