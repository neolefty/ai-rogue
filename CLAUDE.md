# AI Rogue - Project Context for Claude

This document provides context for AI assistants working on this project.

## Project Overview
AI Rogue is a dungeon crawler game that demonstrates AI integration by dynamically generating sprites and monster stats using OpenAI's APIs. It's a fun project designed to showcase AI capabilities to co-workers.

**Current Architecture**: Modular design with separated concerns (June 2025 refactor)
- `game.py` - Main game loop and coordination (139 lines, down from 680+)
- `entities.py` - Clean entity hierarchy (Entity → Monster/Player/LootItem)
- `combat.py` - Multi-target combat system with damage falloff
- `ai_behavior.py` - Monster AI with three-zone behavior and mini-boss clustering
- `rendering.py` - All visual rendering and UI
- `game_state.py` - Game data management
- `ai_client.py` - OpenAI integration for sprites/stats
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
  - Three behavior zones: aggressive (always chase), alert (70% chase chance), passive (wander)
  - Mini-boss clustering: regular monsters are drawn toward mini-bosses
  - Monster separation to prevent pile-ups
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
- `game.py`: Main game logic, sprite generation, and gameplay mechanics
- `prompts.py`: All AI prompts for sprite and stat generation
- `requirements.txt`: Python dependencies
- `.env`: Contains `OPENAI_API_KEY` (not in version control)

## Important Commands
When making code changes, run these commands to ensure code quality:
```bash
# No specific linting or type checking commands are currently configured
# Consider asking the user for their preferred commands if needed
```

## Recent Development Notes
1. **Modular Architecture Refactor (2025-06)**: Complete restructuring from monolithic 680+ line file
   - Separated into focused modules: entities, combat, ai_behavior, rendering, game_state
   - Clean entity hierarchy with proper inheritance
   - Professional structure for team collaboration
2. **Movement System Overhaul**: Normalized 8-directional movement
   - Both player and monsters constrained to 8 directions
   - Diagonal movement normalized to prevent speed exploits
   - Consistent movement feel across all entities
3. **Game Over & Restart System**: Professional death handling
   - Translucent overlay preserves final battle view
   - Complete stats summary (levels, monsters, items)
   - SPACE to restart with persistent loot ("ghost of runs past")
4. **Loot Persistence Mechanics**: 
   - Items persist between levels and through restarts
   - Loot drops near monster death locations (3-tile radius)
   - Creates natural treasure trails and battle graveyards
   - Strategic resource management (save potions for later)
5. **Visual Enhancements**:
   - Health bars show bonus health in cyan (normal in green)
   - Loading screens properly render during sprite generation
   - Consistent translucent overlay system for pause/game over
6. **Combat Rebalance (2025-01)**: Complete overhaul for fast-paced tactical gameplay
   - Player: 5 base HP, 0.5 base damage, weapons give +0.05 damage
   - Monsters: HP = level, damage = level
   - Armor gives +1 HP per piece (critical for survival)
   - Attack cooldowns: 500ms player, 1000ms monsters
7. **AI System**: 
   - Three-zone behavior: aggressive, alert (with mini-boss bias), passive
   - Mini-boss clustering creates tactical group formations
   - 30% chance for monsters to approach nearby mini-bosses
8. **Technical Details**:
   - OpenAI Python Client for sprite/stats generation
   - DALL-E 3 with base64 responses
   - Pygame 2.6.1 with modern window focus events
   - Python 3.13.2 with virtual environment

## Game Balance Philosophy
- **Fast, Tactical Combat**: Low HP pools make positioning and timing critical
- **Risk vs Reward**: Higher level monsters are lethal but drop better loot
- **Kiting Strategy**: Multi-target damage falloff encourages grouping enemies strategically
- **Visual Clarity**: Effect circles provide instant feedback on combat states

## Common Issues & Solutions
1. **NoneType error in image generation**: Ensure `response_format="b64_json"` is included in DALL-E API calls
2. **Busy/complex sprites**: Keep prompts minimal - "Basic human figure" works better than detailed descriptions
3. **Window pause not working**: Remove `pygame.display.get_active()` checks that can conflict with window events
4. **Monster stats vs gameplay**: AI-generated stats are for flavor only; actual combat uses balanced formulas
5. **Visual effect performance**: Effect circles use pygame.SRCALPHA surfaces for transparency

## Cache Structure
- `cache/sprites/`: Player and stairway sprites
- `cache/monsters/`: Monster sprites and stats files (cached by level)
- `cache/items/`: Item sprites (weapon, armor, potion)
- `cache-old-1/`: Previous sprite generation attempts (for comparison)

## Development Workflow
1. Test changes locally before committing
2. Verify sprite generation works with current prompts
3. Check that window focus events trigger properly
4. Ensure game performance remains smooth with generated content