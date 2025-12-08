
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.character.character import Character
from src.character.skills.job_skills.priest_skills import create_priest_skills
from src.character.skills.job_skills.dimensionist_skills import create_dimensionist_skills
from src.character.skills.custom_handlers import execute_custom_handler
from src.character.gimmick_updater import GimmickUpdater
from src.character.skills.effects.buff_effect import BuffType
from src.core.event_bus import event_bus

from src.core.config import initialize_config, config
from src.character.stats import StatManager, Stats

class TestSkillUpdates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize config
        if config is None:
            initialize_config()

    def setUp(self):
        self.priest = Character("Priest", "priest")
        # Initialize stat manager for priest to avoid errors accessing stats
        # StatManager expects stats_config dict
        self.priest.stat_manager = StatManager({})

        self.dimensionist = Character("Dimensionist", "dimensionist")
        self.dimensionist.stat_manager = StatManager({
            "hp": {"base_value": 100}
        })
        
        # Set base stats to ensure max_hp > 0
        self.dimensionist.current_hp = 100
        
        self.dimensionist.refraction_stacks = 50 # Start with some refraction
        
        # Mock status manager
        self.dimensionist.status_manager = MagicMock()
        self.dimensionist.status_manager.get_status_by_name = MagicMock(return_value=None)

    def test_priest_holy_protection_buff_value(self):
        print("\nTesting Priest Holy Protection Buff Value...")
        skills = create_priest_skills()
        # Find skill in list
        divine_protection = next((s for s in skills if s.skill_id == "priest_divine_protection"), None)
        
        self.assertIsNotNone(divine_protection, "Divine Protection skill not found")
        
        def_buff = None
        mdef_buff = None
        
        for effect in divine_protection.effects:
            if hasattr(effect, 'buff_type'):
                if effect.buff_type == BuffType.DEFENSE_UP:
                    def_buff = effect
                elif effect.buff_type == BuffType.MAGIC_DEFENSE_UP:
                    mdef_buff = effect
        
        self.assertIsNotNone(def_buff, "Defense Up buff not found")
        self.assertIsNotNone(mdef_buff, "Magic Defense Up buff not found")
        
        print(f"Defense Buff Value: {def_buff.value}")
        print(f"Magic Defense Buff Value: {mdef_buff.value}")
        
        self.assertEqual(def_buff.value, 0.4, "Defense buff should be 0.4 (40%)")
        self.assertEqual(mdef_buff.value, 0.4, "Magic Defense buff should be 0.4 (40%)")

    def test_refraction_amplifier_duration(self):
        print("\nTesting Refraction Amplifier Duration...")
        skills = create_dimensionist_skills()
        # Find skill in list
        refraction_amplifier = next((s for s in skills if s.skill_id == "dimensionist_refraction_amplifier"), None)
        
        self.assertIsNotNone(refraction_amplifier, "Refraction Amplifier skill not found")
        
        print(f"Refraction Amplifier Description: {refraction_amplifier.description}")
        self.assertIn("5턴", refraction_amplifier.description, "Description should mention 5 turns")

    def test_refraction_shield_prevents_self_damage(self):
        print("\nTesting Refraction Shield Prevents Self-Damage...")
        
        # 1. Without shield
        initial_hp = self.dimensionist.current_hp
        initial_refraction = self.dimensionist.refraction_stacks
        
        GimmickUpdater._update_dimension_refraction(self.dimensionist)
        
        damage_taken = initial_hp - self.dimensionist.current_hp
        refraction_lost = initial_refraction - self.dimensionist.refraction_stacks
        
        print(f"Without Shield: HP Lost={damage_taken}, Refraction Lost={refraction_lost}")
        self.assertGreater(damage_taken, 0, "Should take damage without shield")
        
        # 2. With shield
        self.dimensionist.current_hp = 100
        self.dimensionist.refraction_stacks = 50
        
        # Mock the shield presence
        shield_mock = MagicMock()
        shield_mock.name = "Refraction Shield"
        self.dimensionist.status_manager.get_status_by_name = MagicMock(return_value=shield_mock)
        
        initial_hp = self.dimensionist.current_hp
        initial_refraction = self.dimensionist.refraction_stacks
        
        GimmickUpdater._update_dimension_refraction(self.dimensionist)
        
        damage_taken = initial_hp - self.dimensionist.current_hp
        refraction_lost = initial_refraction - self.dimensionist.refraction_stacks
        
        print(f"With Shield: HP Lost={damage_taken}, Refraction Lost={refraction_lost}")
        
        self.assertEqual(damage_taken, 0, "Should NOT take damage with shield")
        self.assertEqual(refraction_lost, 0, "Refraction should not degrade with shield (stabilized)")

if __name__ == '__main__':
    unittest.main()
