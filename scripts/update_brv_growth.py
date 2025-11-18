"""
모든 직업의 BRV 성장량을 1레벨 수치의 20%로 설정
"""
import yaml
from pathlib import Path

def update_brv_growth():
    """모든 직업 파일의 BRV 성장량 업데이트"""
    characters_dir = Path("data/characters")
    updated_count = 0
    
    for yaml_file in characters_dir.glob("*.yaml"):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # base_stats에서 init_brv와 max_brv 가져오기
            if 'base_stats' not in data:
                print(f"[SKIP] {yaml_file.stem}: base_stats 없음")
                continue
            
            init_brv = data['base_stats'].get('init_brv')
            max_brv = data['base_stats'].get('max_brv')
            
            if init_brv is None or max_brv is None:
                print(f"[SKIP] {yaml_file.stem}: BRV 값 없음")
                continue
            
            # stat_growth 섹션 확인/생성
            if 'stat_growth' not in data:
                data['stat_growth'] = {}
            
            # 1레벨 수치의 20%로 성장량 설정
            new_init_brv_growth = round(init_brv * 0.2, 1)
            new_max_brv_growth = round(max_brv * 0.2, 1)
            
            old_init_brv_growth = data['stat_growth'].get('init_brv', 'N/A')
            old_max_brv_growth = data['stat_growth'].get('max_brv', 'N/A')
            
            data['stat_growth']['init_brv'] = new_init_brv_growth
            data['stat_growth']['max_brv'] = new_max_brv_growth
            
            # 파일 저장
            with open(yaml_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
            
            print(f"[OK] {yaml_file.stem}:")
            print(f"  init_brv: {init_brv} -> 성장량 {old_init_brv_growth} -> {new_init_brv_growth}")
            print(f"  max_brv: {max_brv} -> 성장량 {old_max_brv_growth} -> {new_max_brv_growth}")
            updated_count += 1
            
        except Exception as e:
            print(f"[ERROR] {yaml_file.stem}: {e}")
    
    print(f"\n총 {updated_count}개 직업 업데이트 완료")

if __name__ == "__main__":
    update_brv_growth()

