
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock logger to avoid import issues
class MockLogger:
    def debug(self, msg, *args, **kwargs): print(f"[DEBUG] {msg} {args if args else ''} {kwargs if kwargs else ''}")
    def info(self, msg, *args, **kwargs): print(f"[INFO] {msg} {args if args else ''} {kwargs if kwargs else ''}")
    def warning(self, msg, *args, **kwargs): print(f"[WARN] {msg} {args if args else ''} {kwargs if kwargs else ''}")
    def error(self, msg, *args, **kwargs): print(f"[ERROR] {msg} {args if args else ''} {kwargs if kwargs else ''}")

import src.core.logger
src.core.logger.get_logger = lambda name: MockLogger()

# Initialize Config to avoid errors
from src.core.config import initialize_config
try:
    initialize_config()
except:
    pass

from src.character.skills.skill_manager import get_skill_manager
from src.character.skills.job_skills.sword_saint_skills import register_sword_saint_skills
from src.character.character import Character
from src.core.event_bus import event_bus, Events

# Mock CombatManager for context
class MockCombatManager:
    def __init__(self):
        self.combat_ui = None

# Mock Character
class MockCharacter:
    def __init__(self, name):
        self.name = name
        self.is_alive = True
        self.current_hp = 1000
        self.max_hp = 1000
        self.current_brv = 100
        self.max_brv = 1000
        self.sword_aura = 3  # Start with 3 aura
        self.skill_ids = []
        
        # Stats
        self.physical_attack = 100
        self.physical_defense = 10
        self.magic_attack = 10
        self.magic_defense = 10
        self.hit_rate = 100
        self.evasion = 0
        
        self.active_traits = []
        self._combat_manager_ref = MockCombatManager()
        self.status_manager = MockStatusManager()
        self.card_effects = {} # For checks
    
    def effective_max_mp(self):
        return 100
        
    def take_damage(self, damage, **kwargs):
        self.current_hp -= damage
        print(f"[MOCK] took {damage} damage")
        return damage

# Mock StatusManager
class MockStatusManager:
    def can_act(self): return True
    def can_use_skills(self): return True
    def has_status(self, status): return False
    def get_status(self, status): return None


# Initialize
skill_manager = get_skill_manager()
register_sword_saint_skills(skill_manager)

ilseom_id = "sword_saint_ilseom"
skill = skill_manager.get_skill(ilseom_id)

if not skill:
    print(f"Skill {ilseom_id} not found!")
    exit(1)

print(f"Checking metadata for {ilseom_id}...")
print(f"Metadata: {skill.metadata}")

sword_aura_bonus = skill.metadata.get("sword_aura_bonus_hits")
if sword_aura_bonus:
    mult = sword_aura_bonus.get("multiplier")
    print(f"Multiplier in metadata: {mult} (Expected approx 0.333)")
else:
    print("sword_aura_bonus_hits not found in metadata!")

# Execute
user = MockCharacter("SwordSaint")
target = MockCharacter("Target")
target.status_manager = MockStatusManager() # Explicit

print("Executing skill...")
skill_manager.execute_skill(ilseom_id, user, target)
