import unittest
from unittest.mock import MagicMock, patch
import time
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.world.environmental_effects import EnvironmentalEffectManager, EnvironmentalEffect, EnvironmentalEffectType, EFFECT_CONFIGS

class MockPlayer:
    def __init__(self, hp=100, max_hp=100):
        self.current_hp = hp
        self.max_hp = max_hp
        self.name = "TestPlayer"

class TestEnvironmentalRefactor(unittest.TestCase):
    def setUp(self):
        self.manager = EnvironmentalEffectManager()
        self.player = MockPlayer()

    def test_effect_config_damage(self):
        """Test that apply_effect calculates damage correctly based on config."""
        effect = EnvironmentalEffect(EnvironmentalEffectType.BURNING_FLOOR, intensity=1.0)
        
        # Initial apply (should work if called directly via apply_effect)
        msg = self.manager.apply_effect(effect, self.player, is_movement=False)
        
        # Config: Fixed 15
        expected_damage = 15
        self.assertIsNotNone(msg)
        self.assertEqual(self.player.current_hp, 100 - expected_damage)
        print(f"Direct apply passed: {msg}")

    def test_movement_ignored(self):
        """Test that is_movement=True returns None for converted effects."""
        effect = EnvironmentalEffect(EnvironmentalEffectType.BURNING_FLOOR, intensity=1.0)
        msg = self.manager.apply_effect(effect, self.player, is_movement=True)
        self.assertIsNone(msg)
        self.assertEqual(self.player.current_hp, 100) # No damage
        print("Movement ignore passed")

class MockExplorationSystem:
    def __init__(self, manager):
        self.effect_last_tick_times = {}
        self.max_tick_cleanup_time = time.time()
        self.player = MagicMock()
        self.player.party = [MockPlayer()]
        self.dungeon = MagicMock()
        self.dungeon.environment_effect_manager = manager
        # Add the method we want to test by binding it (or just copying the logic for test)
        # Since we can't easily import ExplorationSystem without dependencies, we'll manually test the logi flow
        # defined in _update_effect_timers_and_apply
    
    def _update_effect_timers_and_apply(self, x, y, current_time_mock):
        # Re-implementation of the logic for testing
        effect_manager = self.dungeon.environment_effect_manager
        messages = []
        
        # Mock effects at tile
        effects = effect_manager.get_effects_at_tile(x, y)
        
        for member in self.player.party:
            member_id = id(member)
            for effect in effects:
                config = effect_manager.get_effect_config(effect.effect_type)
                interval = config.get("interval", 3.0)
                timer_key = (member_id, effect.effect_type)
                last_time = self.effect_last_tick_times.get(timer_key, 0.0)
                
                if current_time_mock - last_time >= interval:
                    msg = effect_manager.apply_effect(effect, member, is_movement=False)
                    if msg:
                        messages.append(msg)
                    self.effect_last_tick_times[timer_key] = current_time_mock
        return messages

class TestTimerLogic(unittest.TestCase):
    def test_timer_logic(self):
        manager = EnvironmentalEffectManager()
        # Mock get_effects_at_tile
        manager.get_effects_at_tile = MagicMock(return_value=[
            EnvironmentalEffect(EnvironmentalEffectType.BURNING_FLOOR, intensity=1.0)
        ])
        
        system = MockExplorationSystem(manager)
        player = system.player.party[0]
        
        # t=1000.0: First check (should trigger because 1000.0 - 0.0 >= 1.5)
        msgs = system._update_effect_timers_and_apply(0, 0, current_time_mock=1000.0)
        self.assertTrue(len(msgs) > 0, "Should trigger on first encounter (t=1000.0 vs last=0.0)")
        self.assertEqual(player.current_hp, 85) # 15 dmg
        
        # t=1000.2 (0.2s later, moved to same/adj tile)
        msgs = system._update_effect_timers_and_apply(0, 1, current_time_mock=1000.2)
        self.assertEqual(len(msgs), 0, "Should NOT trigger (0.2s elapsed < 1.5s)")
        self.assertEqual(player.current_hp, 85)
        
        # t=1001.6 (1.6s later from t=1000.0)
        msgs = system._update_effect_timers_and_apply(0, 1, current_time_mock=1001.6)
        self.assertTrue(len(msgs) > 0, "Should trigger (1.6s elapsed >= 1.5s)")
        self.assertEqual(player.current_hp, 70)

if __name__ == '__main__':
    unittest.main()
