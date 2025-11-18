"""지원사격 시스템 테스트"""
from src.core.config import initialize_config
from src.character.character import Character
from src.character.gimmick_updater import GimmickUpdater
from src.world.enemy_generator import EnemyGenerator

# Config 초기화
initialize_config()

# 궁수 생성
archer = Character('궁수', 'archer')
archer.gimmick_type = 'support_fire'
archer.support_fire_combo = 0
archer.current_brv = 0
archer.max_brv = 1000

# 전사 생성 (공격자)
warrior = Character('전사', 'warrior')

# 적 생성
enemies = EnemyGenerator.generate_enemies(floor_number=1, num_enemies=1)
enemy = enemies[0]

print('=== 초기 상태 ===')
print(f'궁수 BRV: {archer.current_brv}/{archer.max_brv}')
print(f'궁수 콤보: {getattr(archer, "support_fire_combo", 0)}')
print(f'적 HP: {enemy.current_hp}/{enemy.max_hp}')

# 전사에게 일반 화살 마킹
print('\n=== 전사에게 일반 화살 마킹 ===')
setattr(warrior, 'mark_slot_normal', 1)
setattr(warrior, 'mark_shots_normal', 3)
print(f'전사 mark_slot_normal: {getattr(warrior, "mark_slot_normal", 0)}')
print(f'전사 mark_shots_normal: {getattr(warrior, "mark_shots_normal", 0)}')

# 전사가 적 공격 시 지원사격 발동
print('\n=== 전사가 적 공격 (지원사격 발동) ===')
GimmickUpdater.on_ally_attack(warrior, [archer, warrior], target=enemy)

print(f'궁수 BRV: {archer.current_brv}/{archer.max_brv}')
print(f'궁수 콤보: {getattr(archer, "support_fire_combo", 0)}')
print(f'전사 mark_shots_normal: {getattr(warrior, "mark_shots_normal", 0)}')

# 한 번 더 공격 (콤보 증가)
print('\n=== 전사가 다시 공격 (콤보 증가) ===')
GimmickUpdater.on_ally_attack(warrior, [archer, warrior], target=enemy)

print(f'궁수 BRV: {archer.current_brv}/{archer.max_brv}')
print(f'궁수 콤보: {getattr(archer, "support_fire_combo", 0)}')
print(f'전사 mark_shots_normal: {getattr(warrior, "mark_shots_normal", 0)}')

print('\n✅ 지원사격 시스템 테스트 완료')
