import pytest
from unittest.mock import MagicMock
from src.character.character import Character
from src.combat.brave_system import BraveSystem, get_brave_system
from src.combat.atb_system import ATBSystem, ATBGauge
from src.combat.damage_calculator import DamageCalculator, get_damage_calculator
from src.core.event_bus import EventBus, get_event_bus

class TestBreakerRemake:
    @pytest.fixture
    def setup_characters(self):
        # Breaker setup
        breaker = MagicMock(spec=Character)
        breaker.name = "Breaker"
        breaker.job_id = "breaker"
        breaker.physical_attack = 100
        breaker.combo_gauge = 0
        breaker.max_combo_gauge = 100
        breaker.system_traits = ["engine_overclock"] # Default trait
        breaker.traits = []
        breaker.current_brv = 1000
        breaker.max_brv = 2000
        breaker.active_traits = []
        
        # Enemy setup
        enemy = MagicMock(spec=Character)
        enemy.name = "Enemy"
        enemy.current_brv = 100
        enemy.max_brv = 1000
        enemy.is_broken = False
        enemy.is_scattered = False
        enemy.scatter_stacks = 0
        enemy.speed = 100
        enemy.active_buffs = {}
        enemy.physical_defense = 50
        enemy.current_hp = 5000
        enemy.max_hp = 5000
        enemy.active_traits = []
        
        # Mock methods
        enemy.take_damage = MagicMock(side_effect=lambda x: x)
        
        return breaker, enemy

    def test_scatter_trigger(self, setup_characters):
        """Test if SCATTER is triggered when Breaker causes a BREAK"""
        breaker, enemy = setup_characters
        bs = BraveSystem()
        
        # Mock logger
        bs.logger = MagicMock()
        
        # Execute BRV attack that causes break
        # Using a mock for damage calc is hard because brv_attack calls internal logic
        # But brv_attack is mostly self-contained logic for break flag
        
        # Since brv_attack has many dependencies, we might need to integration test
        # or use a simplified mock of BraveSystem that only tests the logic block
        # However, let's try to run the real methods if possible
        
        # Mock event bus to avoid external dependencies
        get_event_bus().publish = MagicMock()
        
        # Setup conditions for break
        enemy.current_brv = 0
        enemy.is_broken = False # ready to be broken logic check: was_broken is checked inside
        # Actually brv_attack checks 'was_broken' based on current_brv <= 0 BEFORE damage?
        # No, "if was_broken and actual_damage > 0 and not already_broken"
        # was_broken = (enemy.current_brv <= 0)
        
        # Force current BRV 0
        enemy.current_brv = 0
        
        # Execute
        result = bs.brv_attack(breaker, enemy, 100)
        
        # Assertions
        assert result['is_break'] == True
        assert enemy.is_scattered == True
        assert enemy.scatter_source == breaker
        assert enemy.scatter_stacks == 0

    def test_scatter_damage_multiplier(self, setup_characters):
        """Test if SCATTER multiplier is applied correctly"""
        breaker, enemy = setup_characters
        dc = DamageCalculator()
        dc.logger = MagicMock()
        
        # Setup SCATTER state
        enemy.is_scattered = True
        enemy.scatter_source = breaker
        enemy.scatter_stacks = 0
        
        # Base damage calc
        # Engine Overclock (trait) should make base 1.85
        # 100 damage -> 185
        
        damage_result, _ = dc.calculate_hp_damage(
            attacker=breaker,
            defender=enemy,
            brv_points=100, # Base damage proportional to BRV
            hp_multiplier=1.0,
            is_break=True # Must be break for Scatter to valid
        )
        
        # Expected: 100 * 1.0 * stat_mod * hp_dmg_mult * SCATTER_MULT
        # stat_mod = 100 / (50+1) ~= 2.0
        # hp_dmg_mult default? usually 1.0 or config dependent. Assuming 1.0 in mock if not mocked
        # DamageCalculator reads self.hp_damage_multiplier. Default is 1.0
        
        base_calc = int(100 * 1.0 * (100/51) * 1.0) # ~196
        expected_mult = 1.85 # Engine Overclock
        expected_dmg = int(base_calc * expected_mult)
        
        # Allow small margin due to int flooring differences
        assert abs(damage_result.final_damage - expected_dmg) < 5
        
        # Test Stacking
        enemy.scatter_stacks = 5
        # 1.85 + (5 * 0.08) = 1.85 + 0.4 = 2.25
        # If Chemical Resonance (0.12)? Breaker active_traits?
        # In setup_characters, breaker has system_traits=['engine_overclock']
        # I didn't add 'chemical_resonance'
        
        damage_result_stacked, _ = dc.calculate_hp_damage(
            attacker=breaker,
            defender=enemy,
            brv_points=100,
            hp_multiplier=1.0,
            is_break=True
        )
        
        expected_mult_stacked = 1.85 + (5 * 0.08)
        expected_dmg_stacked = int(base_calc * expected_mult_stacked)
        
        assert abs(damage_result_stacked.final_damage - expected_dmg_stacked) < 5

    def test_combo_gauge_gain(self, setup_characters):
        """Test if Combo Gauge increases after damage"""
        breaker, enemy = setup_characters
        bs = BraveSystem()
        bs.logger = MagicMock()
        get_event_bus().publish = MagicMock()
        
        # Setup SCATTER
        enemy.is_scattered = True
        enemy.scatter_source = breaker
        enemy.scatter_stacks = 0
        breaker.combo_gauge = 0
        
        # Mock calculate_hp_damage to return fixed high damage
        # We need to ensure damage_calculator logic in BraveSystem.hp_attack works
        # Real damage calc is needed to populate 'details' (actually details logic wasn't fully added for scatter mult)
        # But BraveSystem.hp_attack executes logic to RE-CALCULATE bonus portion.
        
        attacker_atk = 100
        defender_id = enemy
        
        # Execute HP Attack
        # We need brv > 0
        breaker.current_brv = 1000
        
        bs.hp_attack(breaker, enemy, brv_multiplier=10.0)
        
        # Validation
        # Check if combo_gauge increased
        assert breaker.combo_gauge > 0
        # Check if stacks increased
        assert enemy.scatter_stacks == 1

    def test_speed_reduction(self, setup_characters):
        """Test SCATTER speed reduction in ATBSystem"""
        breaker, enemy = setup_characters
        
        # Setup ATB Gauge mock wrapper (ATBSystem uses simple logic)
        gauge = ATBGauge(owner=enemy, speed=100)
        
        # 1. Normal Speed
        speed_normal = gauge.get_effective_speed()
        # 100 * 1.0 = 100
        
        # 2. SCATTER active
        enemy.is_scattered = True
        enemy.scatter_source = breaker # Has engine_overclock, NOT hydraulic_piston
        
        speed_scattered = gauge.get_effective_speed()
        # Base reduction 30% => 70 speed
        
        assert speed_scattered == 70.0
        
        # 3. With Hydraulic Piston
        breaker.traits = [MagicMock(id="hydraulic_piston")]
        breaker.system_traits.append("hydraulic_piston")
        
        speed_heavy = gauge.get_effective_speed()
        # 45% reduction => 55 speed
        
        assert speed_heavy == 55.0
