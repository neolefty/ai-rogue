# AI Rogue - Project Context for Claude

This document provides context for AI assistants working on this project.

## Project Overview
AI Rogue is a dungeon crawler game that demonstrates AI integration by dynamically generating sprites and monster stats using OpenAI's APIs. It's a fun project designed to showcase AI capabilities to co-workers.

## Key Features
- **Dynamic Sprite Generation**: Uses DALL-E 3 to generate pixel art sprites for players, monsters, items, and environment elements
- **AI-Generated Monster Stats**: Uses GPT-3.5 to generate contextual monster statistics based on level
- **Progressive Difficulty**: Monster levels scale with dungeon depth, including miniboss encounters
- **Combat System**: Real-time combat with attack cooldowns and range indicators
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
1. **OpenAI Integration**: Successfully migrated from HTTP API calls to OpenAI Python client
2. **Model Compatibility**: 
   - Using DALL-E 3 for sprite generation (gpt-image-1 requires organization verification)
   - Base64 image responses with `response_format="b64_json"`
3. **Sprite Prompts**: Optimized for simple 8-bit pixel art with minimal details
4. **Window Events**: Using pygame's WINDOWFOCUSLOST/WINDOWFOCUSGAINED events (not deprecated ACTIVEEVENT)

## Common Issues & Solutions
1. **NoneType error in image generation**: Ensure `response_format="b64_json"` is included in DALL-E API calls
2. **Busy/complex sprites**: Keep prompts minimal - "Basic human figure" works better than detailed descriptions
3. **Window pause not working**: Remove `pygame.display.get_active()` checks that can conflict with window events

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