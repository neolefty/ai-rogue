import os
import random
from io import BytesIO

import pygame
import requests
from PIL import Image

from prompts import (
    PLAYER_SPRITE_PROMPT,
    MONSTER_SPRITE_PROMPT,
    ITEM_SPRITE_PROMPT,
    STAIRWAY_SPRITE_PROMPT,
    SPRITE_STYLE,
    MONSTER_STATS_SYSTEM_PROMPT,
    MONSTER_STATS_USER_PROMPT,
)

from .openai_client import client


def generate_sprite(prompt, cache_path, game=None):
    """Generate and cache a sprite using DALL-E"""
    if os.path.exists(cache_path):
        return pygame.image.load(cache_path)

    if game:
        game.loading = True
        game.loading_message = "Generating sprite..."
        game._draw_loading_screen()
        pygame.event.pump()

    try:
        response = client.generate_image(
            prompt=f"{prompt}. {SPRITE_STYLE}",
            size="1024x1024",
            quality="standard",
        )
        image_url = response["data"][0]["url"]

        img_response = requests.get(image_url)
        img = Image.open(BytesIO(img_response.content))
        img = img.convert("RGBA")
        img = img.resize((32, 32), Image.Resampling.NEAREST)

        data = img.getdata()
        new_data = []
        for item in data:
            if item[0] + item[1] + item[2] < 30:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)

        img.putdata(new_data)
        img.save(cache_path, "PNG")

        sprite = pygame.image.load(cache_path)
        if game:
            game.loading = False
        return sprite
    except Exception as e:
        print(f"Error generating sprite: {str(e)}")
        if game:
            game.loading = False
        return pygame.Surface((32, 32))


def generate_monster(level, game=None):
    prompt = MONSTER_SPRITE_PROMPT.format(level=level)
    monster_path = f"cache/monsters/monster_level_{level}.png"
    stats_path = f"cache/monsters/monster_level_{level}_stats.txt"

    if os.path.exists(monster_path) and os.path.exists(stats_path):
        monster_sprite = pygame.image.load(monster_path)
        with open(stats_path, "r") as f:
            monster_stats = f.read()
        return monster_sprite, monster_stats

    monster_sprite = generate_sprite(prompt, monster_path, game)

    if os.path.exists(stats_path):
        with open(stats_path, "r") as f:
            monster_stats = f.read()
    else:
        try:
            response = client.generate_chat_completion(
                [
                    {"role": "system", "content": MONSTER_STATS_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": MONSTER_STATS_USER_PROMPT.format(level=level),
                    },
                ]
            )
            monster_stats = response["choices"][0]["message"]["content"]
            with open(stats_path, "w") as f:
                f.write(monster_stats)
        except Exception as e:
            print(f"Error generating monster stats: {str(e)}")
            monster_stats = f"Level {level} monster"
            with open(stats_path, "w") as f:
                f.write(monster_stats)

    return monster_sprite, monster_stats


def generate_item(game=None):
    item_type = random.choice(["weapon", "armor", "potion"])
    prompt = ITEM_SPRITE_PROMPT.format(item_type=item_type)
    item_path = f"cache/items/item_{item_type}.png"
    sprite = generate_sprite(prompt, item_path, game)
    return sprite, item_type


def generate_stairway(game=None):
    prompt = STAIRWAY_SPRITE_PROMPT
    stairway_path = "cache/sprites/stairway.png"
    sprite = generate_sprite(prompt, stairway_path, game)
    return sprite
