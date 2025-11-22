#!/usr/bin/env python3
"""
Convert logo.png to logo.ico for NSIS installer
"""

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow (PIL) is required. Install it with: pip install Pillow")
    sys.exit(1)

def convert_png_to_ico(png_path, ico_path, sizes=None):
    """Convert PNG to ICO format"""
    if sizes is None:
        # Common ICO sizes
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    
    try:
        # Open the PNG image
        img = Image.open(png_path)
        
        # Create ICO with multiple sizes
        ico_images = []
        for size in sizes:
            resized = img.resize(size, Image.Resampling.LANCZOS)
            ico_images.append(resized)
        
        # Save as ICO
        ico_images[0].save(ico_path, format='ICO', sizes=[(img.width, img.height) for img in ico_images])
        print(f"Successfully converted {png_path} to {ico_path}")
        return True
    except Exception as e:
        print(f"Error converting image: {e}")
        return False

def main():
    png_path = Path("assets/logo.png")
    ico_path = Path("assets/logo.ico")
    
    if not png_path.exists():
        print(f"Error: {png_path} not found")
        sys.exit(1)
    
    if convert_png_to_ico(png_path, ico_path):
        print(f"ICO file created: {ico_path}")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()

