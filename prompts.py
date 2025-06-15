# Prompt constants for AI generation

PLAYER_SPRITE_PROMPT = "Basic human figure with sword"
MONSTER_SPRITE_PROMPT = "Simple monster creature, basic shape"
STAIRWAY_SPRITE_PROMPT = "Simple stone steps going down"

# Item-specific prompts for better variety and detail
WEAPON_SPRITE_PROMPT = "Simple sword shape, plain blade, no decoration"
ARMOR_SPRITE_PROMPT = "Simple helmet or shield shape, basic armor piece"
POTION_SPRITE_PROMPT = "Simple round bottle, colored liquid inside"
DEATH_SPRITE_PROMPT = "Small pile of bones or skull, simple skeleton remains"

# Variant-specific prompts
WEAPON_VARIANTS = {
    "sword": "Simple sword shape, straight blade",
    "axe": "Simple axe shape, wooden handle",
    "dagger": "Simple dagger shape, short blade",
    "mace": "Simple mace shape, spiked head",
    "spear": "Simple spear shape, pointed tip"
}

ARMOR_VARIANTS = {
    "helmet": "Simple helmet shape, basic protection",
    "shield": "Simple shield shape, round or rectangular",
    "chestplate": "Simple armor chestplate, basic metal",
    "gauntlets": "Simple gauntlets shape, hand protection",
    "boots": "Simple boots shape, armored footwear"
}

POTION_VARIANTS = {
    "bottle": "Simple round bottle, colored liquid inside",
    "vial": "Simple vial shape, thin glass container",
    "flask": "Simple flask shape, wide bottom container",
    "orb": "Simple orb shape, glowing magical sphere",
    "crystal": "Simple crystal shape, gem-like container"
}

SPRITE_STYLE = (
    "Style: Extremely simple 8-bit pixel art from 1980s video games. "
    "Maximum 4 colors total, very chunky pixels, no fine details whatsoever. "
    "Pure black background (#000000), no gradients, no shading, no outlines, no text. "
    "Must be recognizable in under 16x16 pixels, minimal and iconic only."
)

MONSTER_STATS_SYSTEM_PROMPT = "You are a dungeon monster generator."
MONSTER_STATS_USER_PROMPT = "Generate stats for a level {level} monster."

DUNGEON_MONSTER_DESCRIPTION_PROMPT = (
    "Generate a unique monster name and description for level {level}"
)
