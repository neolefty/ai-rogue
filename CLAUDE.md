# AI Rogue - Project Context for Claude

This document provides context for AI assistants working on this project.

## Project Overview
AI Rogue is a dungeon crawler game that demonstrates AI integration by dynamically generating sprites and monster stats using OpenAI's APIs. It's a fun project designed to showcase AI capabilities to co-workers.

**Current Architecture**: Modular design with separated concerns
- `game.py` - Main game loop and coordination
- `entities.py` - Clean entity hierarchy (Entity → Monster/Player/LootItem/Stairway)
- `combat.py` - Multi-target combat system with damage falloff
- `ai_behavior.py` - Monster AI with three-zone behavior and clustering/dispersion
- `rendering.py` - All visual rendering and UI
- `game_state.py` - Game data management
- `ai_client.py` - OpenAI integration for sprites/stats
- `sprite_manager.py` - Background sprite generation with placeholders
- `image_utils.py` - Shared image processing utilities
- `constants.py` - All game configuration
- `prompts.py` - AI generation prompts

## Key Features
- **Dynamic Sprite Generation**: Uses DALL-E 3 to generate pixel art sprites for players, monsters, items, and environment elements
- **AI-Generated Monster Stats**: Uses GPT-3.5 to generate contextual monster statistics based on level (visual only, gameplay uses balanced formulas)
- **Progressive Difficulty**: Monster levels scale with dungeon depth, including miniboss encounters
- **Fast-Paced Combat System**: 
  - Multi-target attacks with distance-based damage falloff (1st target full damage, 2nd gets 1/2, 3rd gets 1/3, etc.)
  - Quick combat timing (player attacks every 0.5s, monsters every 1s)
  - Low HP, high damage for tactical gameplay
- **Advanced Monster AI**: 
  - Three behavior zones: aggressive (≤150px), alert (≤300px), passive
  - Mini-boss clustering and smart dispersion system
  - Dynamic behavior switching with collision priority
- **Visual Effect System**: Colorblind-friendly circles showing attack states (red=damage taken, cyan=damage dealt, green=ready, gray=cooldown)
- **Loot System**: Weapon, armor, and potion drops that enhance player capabilities
- **Window Focus Pause**: Game automatically pauses when window loses focus

## Technical Stack
- **Python 3.13.2** with virtual environment (`venv/`)
- **pygame 2.6.1** for game engine
- **OpenAI Python Client 1.86.0** for AI integration
- **PIL/Pillow** for image processing
- **python-dotenv** for environment variable management

## Key Files
- `game.py`: Main game loop and event handling
- `ai_client.py`: OpenAI integration for DALL-E and GPT
- `sprite_manager.py`: Background sprite generation with threading
- `prompts.py`: Specialized AI prompts for each sprite type
- `image_utils.py`: Shared image processing utilities
- `.env`: Contains `OPENAI_API_KEY` (not in version control)

## Important Commands
When making code changes, run these commands to ensure code quality:
```bash
# No specific linting or type checking commands are currently configured
# Consider asking the user for their preferred commands if needed
```

## Current System Status (2025-06)
**Architecture**: Fully modular with clean separation of concerns and comprehensive documentation

**Key Systems**:
- **Combat**: Multi-target attacks with damage falloff (1st full, 2nd ½, 3rd ⅓, etc.)
- **AI Behavior**: Three-zone system with clustering/dispersion (aggressive ≤150px, alert ≤300px, passive)
- **Sprite Generation**: Background threading with placeholders, specialized prompts per item type
- **Game Flow**: Persistent loot, translucent overlays, 8-directional normalized movement

**Balance**: Fast-paced tactical gameplay - Player: 5 HP + armor, 0.5s attacks; Monsters: HP=level, 1s attacks

## Game Balance Philosophy
- **Fast, Tactical Combat**: Low HP pools make positioning and timing critical
- **Risk vs Reward**: Higher level monsters are lethal but drop better loot
- **Kiting Strategy**: Multi-target damage falloff encourages grouping enemies strategically
- **Visual Clarity**: Effect circles provide instant feedback on combat states

## Common Issues & Solutions
1. **Complex sprites**: Use simple, specific prompts - "Simple sword shape, plain blade, no decoration"
2. **Monster stats vs gameplay**: AI-generated stats are for flavor only; actual combat uses balanced formulas
3. **Threading issues**: All sprite generation uses background threads with placeholder system

## Cache Structure
- `cache/sprites/`: Player and stairway sprites
- `cache/monsters/`: Monster sprites and stats files (cached by level)
- `cache/items/`: Item sprites with specialized prompts (weapon, armor, potion)

## Development Workflow
1. Test changes locally before committing
2. Verify sprite generation works with current specialized prompts
3. Check that AI behavior systems work as intended
4. Ensure threading and background generation remain stable