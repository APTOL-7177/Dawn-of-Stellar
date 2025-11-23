# Bot System Removal - Code Cleanup Guide

## Archived Files
The following bot-related files have been moved to `archive/`:
- `multiplayer/ai_bot.py`
- `multiplayer/ai_bot_advanced.py` 
- `multiplayer/bot_communication.py`
- `multiplayer/bot_tasks.py`
- `ui/bot_help_ui.py`
- `ui/bot_inventory_ui.py`

## Files with Bot References

### src/ui/world_ui.py
Contains extensive bot-related code:
- Line 56: `self.current_bot_view_index`
- Lines 66-67: Bot help UI initialization
- Lines 199-226: Bot inventory UI handling
- Lines 238-249: Bot command processing
- Lines 945-971: Bot rendering
- Lines 1382-1447: Bot chat and update logic

**Recommendation**: These sections are non-critical for core functionality. They can remain as-is since bot files are archived. If errors occur, simply comment out or remove the bot-related sections.

### src/ui/multiplayer_party_setup.py
Contains bot auto-select logic:
- Lines 247-277: Bot turn processing

**Recommendation**: Can be left as-is since it only activates when bot_manager exists.

## Multiplayer Compatibility

### Town System
- Each player now has their own `FloorTransitionManager` instance
- Uses player_id to track individual progress
- Automatic ready state when leaving town

### Changes Made
1. **FloorTransitionManager**: Now supports `player_id` parameter
2. **Global manager**: Changed to dictionary-based `_floor_transition_managers`
3. **Auto-ready**: Players automatically become ready when leaving town

## Notes
- Bot code references in UI files are safe to leave (will simply not execute without bot_manager)
- All bot functionality is disabled by archiving the core bot files
- No breaking changes to core game systems
