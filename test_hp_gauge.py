"""HP 게이지 빗금 문제 디버깅 스크립트"""
import sys
sys.path.insert(0, 'src')

from src.ui.gauge_tileset import GaugeTileManager
import tcod.tileset

# 타일셋 초기화
tileset = tcod.tileset.load_truetype_font("GalmuriMono9.ttf", 14, 13)
manager = GaugeTileManager()
manager.initialize(tileset)

# 테스트 케이스: wound_pixels=0 (빗금이 없어야 함)
print("\n=== 테스트 1: wound_pixels=0 (빗금 없어야 함) ===")
for hp in [32, 20, 10, 5]:
    tile_char = manager.create_boundary_tile(
        hp_pixels=hp,
        wound_pixels=0,  # 상처 없음!
        hp_color=(220, 50, 50),  # 빨강
        bg_color=(80, 20, 20),
        wound_color=(80, 35, 55),
        wound_stripe_color=(0, 0, 0),
        cell_index=0
    )
    print(f"  HP={hp}, wound=0 → tile_char={repr(tile_char)}, ord={ord(tile_char) if tile_char != ' ' else 0}")

# 테스트 케이스: wound_pixels>0 (빗금이 있어야 함)
print("\n=== 테스트 2: wound_pixels>0 (빗금 있어야 함) ===")
for wound in [32, 20, 10, 5]:
    tile_char = manager.create_boundary_tile(
        hp_pixels=0,
        wound_pixels=wound,  # 상처 있음!
        hp_color=(220, 50, 50),
        bg_color=(80, 20, 20),
        wound_color=(80, 35, 55),
        wound_stripe_color=(0, 0, 0),
        cell_index=0
    )
    print(f"  HP=0, wound={wound} → tile_char={repr(tile_char)}, ord={ord(tile_char) if tile_char != ' ' else 0}")

# 테스트 케이스: HP + wound 혼합 (빗금은 상처 영역만)
print("\n=== 테스트 3: HP + wound 혼합 (경계 타일) ===")
for hp, wound in [(20, 12), (10, 22), (16, 16)]:
    tile_char = manager.create_boundary_tile(
        hp_pixels=hp,
        wound_pixels=wound,
        hp_color=(220, 50, 50),
        bg_color=(80, 20, 20),
        wound_color=(80, 35, 55),
        wound_stripe_color=(0, 0, 0),
        cell_index=0
    )
    print(f"  HP={hp}, wound={wound} → tile_char={repr(tile_char)}, ord={ord(tile_char) if tile_char != ' ' else 0}")

print("\n=== 캐시 상태 ===")
if hasattr(manager, '_boundary_tile_cache'):
    print(f"  캐시 크기: {len(manager._boundary_tile_cache)}")
    print(f"  다음 코드포인트: 0x{manager._next_boundary_codepoint:04X}")
else:
    print("  캐시 없음")

print("\n완료!")
