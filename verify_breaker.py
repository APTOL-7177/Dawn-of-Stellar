import sys
import os
import logging

# Setup path
sys.path.append(os.getcwd())

# Setup basic logging
logging.basicConfig(level=logging.INFO)

# Import mocks and classes
from unittest.mock import MagicMock
from src.character.character import Character
from src.combat.brave_system import BraveSystem, get_brave_system
from src.combat.atb_system import ATBSystem, ATBGauge
from src.combat.damage_calculator import DamageCalculator, get_damage_calculator
from src.core.event_bus import EventBus, event_bus
from src.core.config import initialize_config

# Initialize config
try:
    initialize_config()
except Exception:
    pass # Already initialized or error handled elsewhere

def setup_characters():
    # Breaker setup
    breaker = MagicMock(spec=Character)
    breaker.name = "Breaker"
    breaker.job_id = "breaker"
    breaker.physical_attack = 100
    breaker.combo_gauge = 0
    breaker.max_combo_gauge = 100
    breaker.system_traits = ["engine_overclock"]
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
    
    # Mock specific methods
    enemy.take_damage = MagicMock(side_effect=lambda x: x)
    
    return breaker, enemy

def test_scatter_trigger():
    print("Testing SCATTER Trigger...", end=" ")
    breaker, enemy = setup_characters()
    bs = BraveSystem()
    bs.logger = MagicMock()
    # Mock publish on the actual event_bus instance
    event_bus.publish = MagicMock()
    
    enemy.current_brv = 0
    
    # Force mock for is_broken getter in BraveSystem
    # But BraveSystem.is_broken just reads attr. My mock has attr.
    # The real BraveSystem instantiates DamageCalculator, which might read stats
    
    # Real execution
    try:
        result = bs.brv_attack(breaker, enemy, 100)
    except Exception as e:
        print(f"FAIL: {e}")
        import traceback
        traceback.print_exc()
        return

    if result.get('is_break') and enemy.is_scattered and enemy.scatter_source == breaker:
        print("PASS")
    else:
        print(f"FAIL (Break:{result.get('is_break')}, Scatter:{enemy.is_scattered})")

def test_scatter_damage():
    print("Testing SCATTER Damage Multiplier...", end=" ")
    breaker, enemy = setup_characters()
    dc = DamageCalculator()
    dc.logger = MagicMock()
    
    enemy.is_scattered = True
    enemy.scatter_source = breaker
    enemy.scatter_stacks = 0
    
    # Needs to mock _get_attack_stat etc if using real DC
    # Or just mock the stat check methods on DC instance
    dc._get_attack_stat = MagicMock(return_value=100)
    dc._get_defense_stat = MagicMock(return_value=50)
    dc._check_critical = MagicMock(return_value=False)
    dc.check_hit = MagicMock(return_value=True)
    
    # 100 * 1.0 * (100/51) * 1.5(Scatter Base 1.5, wait, Engine Overclock -> 1.85)
    # Breaker has engine_overclock in system_traits. Code checks implementation details.
    
    res, _ = dc.calculate_hp_damage(breaker, enemy, 100, 1.0, is_break=True)
    
    expected_mult = 1.85
    base_calc = int(100 * (100/51) * 1.0) # ~196
    expected = int(base_calc * expected_mult)
    
    if abs(res.final_damage - expected) < 10:
        print(f"PASS (Dmg: {res.final_damage}, Exp: {expected})")
    else:
        print(f"FAIL (Dmg: {res.final_damage}, Exp: {expected})")

def test_combo_gauge():
    print("Testing Combo Gauge Gain...", end=" ")
    breaker, enemy = setup_characters()
    bs = BraveSystem()
    bs.logger = MagicMock()
    event_bus.publish = MagicMock()
    
    enemy.is_scattered = True
    enemy.scatter_source = breaker
    enemy.scatter_stacks = 0
    
    # Needed for hp_attack internal checks
    # We will assume real DamageCalculator works if imports work.
    
    # Mocking dependencies for DC
    # DC needs stats.
    enemy.physical_defense = 0 # Simplify
    breaker.physical_attack = 100
    
    # Mock get_damage_calculator to return local DC mock or pre-setup DC?
    # BraveSystem calls get_damage_calculator() -> returns singleton.
    # We can inject our mocked DC into the singleton accessor or patching
    # But for simplicity, we let it create a new one (it's stateless mostly).
    # We just need mocking stats on char objects.
    
    # We also need to mock DifficultySystem and other singletons if they ARE used.
    # DamageCalculator imports get_difficulty_system inside function.
    # We should probably mock sys.modules['src.core.difficulty'] or similar if it fails.
    # But let's try.
    
    try:
        bs.hp_attack(breaker, enemy, brv_multiplier=1.0)
    except Exception as e:
        print(f"FAIL: {e}")
        import traceback
        traceback.print_exc()
        return
        
    if breaker.combo_gauge > 0:
        print(f"PASS (Gauge: {breaker.combo_gauge})")
    else:
        print(f"FAIL (Gauge: {breaker.combo_gauge})")

def test_speed_reduction():
    print("Testing SCATTER Speed Reduction...", end=" ")
    breaker, enemy = setup_characters()
    enemy.is_scattered = True
    enemy.scatter_source = breaker
    
    gauge = ATBGauge(enemy, 100)
    
    # Breaker has engine_overclock (default). SCATTER base slow 30%.
    # If I add hydraulic_piston -> 45%.
    
    speed = gauge.get_effective_speed()
    # 70 expected
    if abs(speed - 70.0) < 0.1:
        print("PASS")
    else:
        print(f"FAIL (Speed: {speed})")

if __name__ == "__main__":
    test_scatter_trigger()
    test_scatter_damage()
    test_combo_gauge()
    test_speed_reduction()
