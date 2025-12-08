
import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.getcwd())

from src.character.gimmick_updater import GimmickUpdater
from src.character.stats import StatManager, Stats
from src.core.event_bus import Events

class MockCharacter:
    def __init__(self, name="Berserker"):
        self.name = name
        self.gimmick_type = "madness_threshold"
        self.max_hp = 1000
        self.current_hp = 1000
        self.madness = 0
        self.max_madness = 100
        self.rampage_threshold = 100
        self.optimal_min = 30
        self.optimal_max = 70
        self.stat_manager = MagicMock()
        self.stat_manager.get_value.return_value = 100  # Mock base stats
        
        # Mocking generic attributes
        self.active_traits = []

def reproduce_bug():
    print("=== Berserker HP Drain UI Event Reproduction ===")
    
    char = MockCharacter()
    
    # Mock event_bus
    with patch('src.character.gimmick_updater.event_bus') as mock_event_bus:
        # 1. Test Danger Zone (Madness 80)
        print("\n[Test 1] Danger Zone (Madness 80)")
        char.madness = 80
        GimmickUpdater._update_madness_threshold(char, is_turn_end=True)
        
        expected_hp = 1000 - int(1000 * 0.05) # 950
        if char.current_hp == expected_hp:
             print(f"[LOGIC PASS] HP reduced to {char.current_hp}")
        else:
             print(f"[LOGIC FAIL] HP is {char.current_hp}")
             
        # Verify Event Emission
        # Check if publish was called with CHARACTER_HP_CHANGE
        event_called = False
        for call in mock_event_bus.publish.call_args_list:
            if call[0][0] == Events.CHARACTER_HP_CHANGE:
                event_called = True
                print("[EVENT PASS] CHARACTER_HP_CHANGE event emitted!")
                break
        
        if not event_called:
            print("[EVENT FAIL] CHARACTER_HP_CHANGE event NOT emitted!")

        # Reset HP and mock
        char.current_hp = 1000
        mock_event_bus.reset_mock()

        # 2. Test Rampage Zone (Madness 100)
        print("\n[Test 2] Rampage Zone (Madness 100)")
        char.madness = 100
        GimmickUpdater._update_madness_threshold(char, is_turn_end=True)
        
        expected_hp_rampage = 1000 - int(1000 * 0.10) # 900
        if char.current_hp == expected_hp_rampage:
            print(f"[LOGIC PASS] HP reduced to {char.current_hp}")
        else:
            print(f"[LOGIC FAIL] HP is {char.current_hp}")

        # Verify Event Emission
        event_called = False
        for call in mock_event_bus.publish.call_args_list:
            if call[0][0] == Events.CHARACTER_HP_CHANGE:
                event_called = True
                print("[EVENT PASS] CHARACTER_HP_CHANGE event emitted!")
                break
        
        if not event_called:
            print("[EVENT FAIL] CHARACTER_HP_CHANGE event NOT emitted!")

if __name__ == "__main__":
    reproduce_bug()
