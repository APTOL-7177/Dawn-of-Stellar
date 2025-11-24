import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.character.character import Character
from src.character.trait_effects import TraitEffectManager, TraitEffectType
from src.character.skills.skill import Skill
from src.combat.status_effects import StatusEffect, StatusType, StatusManager

class TestOrganicTraits(unittest.TestCase):
    def setUp(self):
        self.trait_manager = TraitEffectManager()
        self.character = MagicMock(spec=Character)
        self.character.name = "Alucard"
        self.character.active_traits = []
        self.character.system_traits = ['vampire_thirst_gimmick']
        self.character.gimmick = MagicMock()
        self.character.gimmick.thirst_value = 10 # Satisfied
        self.character.status_manager = MagicMock(spec=StatusManager)
        self.character.current_hp = 100
        self.character.max_hp = 100
        self.character.current_brv = 50
        self.character.max_brv = 200
        
        # Mock heal method
        def mock_heal(amount):
            actual = min(amount, self.character.max_hp - self.character.current_hp)
            self.character.current_hp += actual
            return actual
        self.character.heal = MagicMock(side_effect=mock_heal)

    def test_lifesteal_multipliers(self):
        print("\n--- Testing Lifesteal Multipliers ---")
        # Satisfied (0-30) -> 1.25x
        self.character.gimmick.thirst_value = 10
        mult = self.trait_manager.calculate_lifesteal_multiplier(self.character)
        print(f"Satisfied Multiplier: {mult} (Expected 1.25)")
        self.assertAlmostEqual(mult, 1.25)

        # Thirsty (31-60) -> 1.5x
        self.character.gimmick.thirst_value = 40
        mult = self.trait_manager.calculate_lifesteal_multiplier(self.character)
        print(f"Thirsty Multiplier: {mult} (Expected 1.5)")
        self.assertAlmostEqual(mult, 1.5)

        # Extreme (61-90) -> 2.0x
        self.character.gimmick.thirst_value = 70
        mult = self.trait_manager.calculate_lifesteal_multiplier(self.character)
        print(f"Extreme Multiplier: {mult} (Expected 2.0)")
        self.assertAlmostEqual(mult, 2.0)

        # Frenzy (91-100) -> 2.75x
        self.character.gimmick.thirst_value = 95
        mult = self.trait_manager.calculate_lifesteal_multiplier(self.character)
        print(f"Frenzy Multiplier: {mult} (Expected 2.75)")
        self.assertAlmostEqual(mult, 2.75)

    def test_sanguine_arts(self):
        print("\n--- Testing Sanguine Arts ---")
        self.character.active_traits = ['sanguine_arts']
        
        # Magic Skill
        skill = MagicMock(spec=Skill)
        skill.is_magic = True # Assuming logic checks this or metadata
        # Note: My implementation checks condition="magic_skill". 
        # In _check_condition, "magic_skill" checks context.get('skill').is_magic or skill_type == MAGIC
        skill.skill_type = "MAGIC"
        
        rate = self.trait_manager.calculate_lifesteal(self.character, skill=skill)
        print(f"Magic Skill Lifesteal Rate: {rate} (Expected 0.20)")
        self.assertAlmostEqual(rate, 0.20)
        
        # Physical Skill
        skill.skill_type = "PHYSICAL"
        rate = self.trait_manager.calculate_lifesteal(self.character, skill=skill)
        print(f"Physical Skill Lifesteal Rate: {rate} (Expected 0.0)")
        self.assertAlmostEqual(rate, 0.0)

    def test_vitality_overflow(self):
        print("\n--- Testing Vitality Overflow ---")
        # This logic is in Skill.execute, so we need to test Skill.execute or simulate it.
        # But I also added logic to LifestealEffect.
        # Let's test LifestealEffect logic first as it's easier to isolate if I import it.
        
        from src.character.skills.effects.lifesteal_effect import LifestealEffect
        
        self.character.active_traits = ['vitality_overflow']
        self.character.current_hp = 100 # Full HP
        self.character.max_hp = 100
        self.character.current_brv = 50
        self.character.max_brv = 200
        
        effect = LifestealEffect(value=0.5) # 50% lifesteal
        # Mock context
        context = {'damage_dealt': 100} # 50 heal
        
        # Execute effect
        result = effect.execute(self.character, None, context)
        
        print(f"Effect Result: {result.message}")
        print(f"Current BRV: {self.character.current_brv} (Expected 100: 50 base + 50 overflow)")
        self.assertEqual(self.character.current_brv, 100)

    def test_bleeding_heart(self):
        print("\n--- Testing Bleeding Heart ---")
        self.character.active_traits = ['bleeding_heart']
        
        target = MagicMock()
        target.status_manager = MagicMock()
        target.status_manager.has_status.return_value = True # Has Bleed
        
        # Check Critical Bonus
        bonus = self.trait_manager.calculate_critical_bonus(self.character, target=target)
        print(f"Crit Bonus vs Bleeding: {bonus} (Expected 0.30)")
        self.assertAlmostEqual(bonus, 0.30)
        
        # Check Critical Damage
        dmg = self.trait_manager.calculate_critical_damage(self.character, target=target)
        print(f"Crit Dmg vs Bleeding: {dmg} (Expected 1.80: 1.5 base + 0.3 trait)")
        # Base is 1.5 usually? calculate_critical_damage returns multiplier.
        # Default multiplier is 1.5. Trait adds 0.3. So 1.8.
        self.assertAlmostEqual(dmg, 1.80)

    def test_shadow_veil(self):
        print("\n--- Testing Shadow Veil ---")
        self.character.active_traits = ['shadow_veil']
        
        # Evasion Bonus
        stats = self.trait_manager.calculate_stat_bonus(self.character)
        print(f"Evasion Multiplier: {stats.get('evasion', 1.0)} (Expected 1.15)")
        self.assertAlmostEqual(stats.get('evasion', 1.0), 1.15)
        
        # Turn Start Low HP -> Stealth
        self.character.current_hp = 20 # 20/100 = 20% < 30%
        self.character.status_manager.add_status = MagicMock()
        
        # Trigger turn start effects
        self.trait_manager.apply_turn_start_effects(self.character)
        
        # Check if stealth added
        print("Checking Stealth Application...")
        self.character.status_manager.add_status.assert_called()
        call_args = self.character.status_manager.add_status.call_args[0][0]
        print(f"Status Added: {call_args.status_type} (Expected STEALTH)")
        self.assertEqual(call_args.status_type, StatusType.STEALTH)

if __name__ == '__main__':
    unittest.main()
