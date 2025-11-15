#!/usr/bin/env python3
"""
BDF 폰트를 PNG 타일셋으로 변환

Usage:
    python scripts/bdf_to_png.py GalmuriMono9.bdf output.png
"""

import sys
import re
from PIL import Image, ImageDraw

def parse_bdf(bdf_path):
    """BDF 파일 파싱"""
    with open(bdf_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # 폰트 정보 추출
    font_info = {}

    # FONTBOUNDINGBOX 추출
    bbx_match = re.search(r'FONTBOUNDINGBOX (\d+) (\d+) (-?\d+) (-?\d+)', content)
    if bbx_match:
        font_info['width'] = int(bbx_match.group(1))
        font_info['height'] = int(bbx_match.group(2))

    # 모든 문자 추출
    chars = {}
    char_blocks = re.finditer(
        r'STARTCHAR\s+(\S+).*?ENCODING\s+(\d+).*?BBX\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(-?\d+).*?BITMAP\s+(.*?)ENDCHAR',
        content,
        re.DOTALL
    )

    for match in char_blocks:
        char_name = match.group(1)
        encoding = int(match.group(2))
        bbx_width = int(match.group(3))
        bbx_height = int(match.group(4))
        bbx_x_offset = int(match.group(5))
        bbx_y_offset = int(match.group(6))
        bitmap_hex = match.group(7).strip().split()

        chars[encoding] = {
            'name': char_name,
            'width': bbx_width,
            'height': bbx_height,
            'x_offset': bbx_x_offset,
            'y_offset': bbx_y_offset,
            'bitmap': bitmap_hex
        }

    return font_info, chars

def render_char(char_data, cell_width, cell_height):
    """단일 문자를 이미지로 렌더링"""
    img = Image.new('RGBA', (cell_width, cell_height), (0, 0, 0, 0))
    pixels = img.load()

    bitmap = char_data['bitmap']
    char_width = char_data['width']
    char_height = char_data['height']
    x_offset = char_data['x_offset']
    y_offset = char_data['y_offset']

    # 중앙 정렬 (공백 제거를 위해 왼쪽 정렬)
    start_x = 0  # x_offset 대신 0으로 (공백 제거)
    start_y = cell_height - char_height - y_offset - 2

    for row_idx, hex_row in enumerate(bitmap):
        # 16진수를 2진수로 변환
        bits = bin(int(hex_row, 16))[2:].zfill(char_width)

        for col_idx, bit in enumerate(bits[:char_width]):
            if bit == '1':
                x = start_x + col_idx
                y = start_y + row_idx
                if 0 <= x < cell_width and 0 <= y < cell_height:
                    pixels[x, y] = (255, 255, 255, 255)

    return img

def create_tilesheet(font_info, chars, output_path, cell_width=10, cell_height=13):
    """PNG 타일셋 생성"""
    # 유니코드 범위 결정 (0x0000 ~ 0xFFFF)
    max_char = 256  # 기본 256문자 (16x16 격자)

    # 필요한 문자만 포함 (ASCII + 한글 + 특수문자)
    important_ranges = [
        (0x0020, 0x007F),   # ASCII
        (0x2500, 0x257F),   # Box Drawing
        (0x2580, 0x259F),   # Block Elements
        (0xAC00, 0xD7A3),   # 한글
    ]

    # 격자 크기 계산
    cols = 16
    rows = 16

    # 전체 이미지 생성
    img_width = cols * cell_width
    img_height = rows * cell_height
    tilesheet = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))

    print(f"타일셋 생성: {img_width}x{img_height} ({cols}x{rows} 격자)")
    print(f"셀 크기: {cell_width}x{cell_height}")
    print(f"총 문자 수: {len(chars)}")

    # 문자 배치
    placed = 0
    for encoding, char_data in sorted(chars.items()):
        if encoding >= 256:
            continue  # 기본 256문자만 (확장 가능)

        # 격자 위치 계산
        col = encoding % cols
        row = encoding // cols

        # 문자 렌더링
        char_img = render_char(char_data, cell_width, cell_height)

        # 타일셋에 붙여넣기
        x = col * cell_width
        y = row * cell_height
        tilesheet.paste(char_img, (x, y), char_img)

        placed += 1
        if placed % 100 == 0:
            print(f"  배치 완료: {placed}/{len(chars)}")

    # 저장
    tilesheet.save(output_path)
    print(f"\n✓ 타일셋 저장: {output_path}")
    print(f"  총 {placed}개 문자 배치")

    return cols, rows, cell_width, cell_height

def main():
    if len(sys.argv) < 3:
        print("Usage: python bdf_to_png.py <input.bdf> <output.png>")
        sys.exit(1)

    bdf_path = sys.argv[1]
    output_path = sys.argv[2]

    print(f"BDF 파일 읽기: {bdf_path}")
    font_info, chars = parse_bdf(bdf_path)

    print(f"폰트 정보:")
    print(f"  크기: {font_info['width']}x{font_info['height']}")
    print(f"  문자 수: {len(chars)}")

    # PNG 타일셋 생성 (공백 제거를 위해 width를 9로 설정)
    cell_width = 9   # 한글 실제 너비 (10 → 9로 줄여서 공백 제거)
    cell_height = 13

    create_tilesheet(font_info, chars, output_path, cell_width, cell_height)

    print(f"\n사용 방법:")
    print(f"  tcod.tileset.load_tilesheet('{output_path}', 16, 16, tcod.tileset.CHARMAP_CP437)")

if __name__ == '__main__':
    main()
