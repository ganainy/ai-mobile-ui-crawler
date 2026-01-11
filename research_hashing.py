
import os
import sys
from PIL import Image
import imagehash

def calculate_hashes(directory):
    files = sorted([f for f in os.listdir(directory) if f.endswith('.png')])
    images = {}
    for f in files:
        try:
            img = Image.open(os.path.join(directory, f))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            images[f] = img
        except Exception as e:
            print(f"Error loading {f}: {e}")

    print(f"Loaded {len(images)} images.")
    
    # 1. Test Current (pHash size=16)
    print("\n--- Current (pHash, size=16) ---")
    h16 = {name: imagehash.phash(img, hash_size=16) for name, img in images.items()}
    print_distance_matrix(files, h16)

    # 2. Test Smaller (pHash size=8)
    print("\n--- Smaller (pHash, size=8) ---")
    h8 = {name: imagehash.phash(img, hash_size=8) for name, img in images.items()}
    print_distance_matrix(files, h8)

    # 3. Test dHash (size=8)
    print("\n--- dHash (Difference Hash, size=8) ---")
    d8 = {name: imagehash.dhash(img, hash_size=8) for name, img in images.items()}
    print_distance_matrix(files, d8)

def print_distance_matrix(files, hashes):
    print("      ", end="")
    for i in range(len(files)):
        print(f" {i:2d} ", end="")
    print()

    for i, f1 in enumerate(files):
        print(f"{i:2d}    ", end="")
        for j, f2 in enumerate(files):
            dist = hashes[f1] - hashes[f2]
            print(f" {dist:2d} ", end="")
        print(f"  {f1}")

if __name__ == "__main__":
    directory = r"E:\VS-projects\mobile-crawler\screenshots\run_88"
    if os.path.exists(directory):
        calculate_hashes(directory)
    else:
        print(f"Directory not found: {directory}")
