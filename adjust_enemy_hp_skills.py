#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""적 스킬 HP 공격 계수 조정 스크립트"""
import re

# 파일 읽기
with open('src/combat/enemy_skills.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

changes = 0
i = 0

while i < len(lines):
    line = lines[i]
    
    # damage_multiplier를 찾으면
    if 'damage_multiplier=' in line:
        # 같은 스킬 정의 내에서 brv_damage와 hp_attack 찾기
        brv = False
        hp = False
        
        # 최대 15줄 앞뒤에서 찾기
        start = max(0, i - 10)
        end = min(len(lines), i + 15)
        
        for j in range(start, end):
            if 'brv_damage=1' in lines[j]:
                brv = True
            if 'hp_attack=True' in lines[j]:
                hp = True
        
        # damage_multiplier 값 추출 및 수정
        match = re.search(r'damage_multiplier=([\d.]+)', line)
        if match:
            val = float(match.group(1))
            new_val = val
            
            # HP 공격만 있는 경우: 1/2
            if hp and not brv:
                new_val = val * 0.5
                changes += 1
                lines[i] = re.sub(r'damage_multiplier=[\d.]+', f'damage_multiplier={new_val}', line)
                print(f"변경 (HP만): {line.strip()} -> {lines[i].strip()}")
            
            # 둘 다 있는 경우: BRV는 2배 적용되었으므로, HP 공격 계수는 1/2로 조정
            # 하지만 damage_multiplier가 하나만 있으므로, 실행 시점에서 조정 필요
            # 일단 그대로 둠 (나중에 실행 시점에서 처리)
    
    i += 1

# 파일 쓰기
with open('src/combat/enemy_skills.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"\n총 {changes}개의 HP 공격 스킬 damage_multiplier 수정 완료")

