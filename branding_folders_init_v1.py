import os

BASE = r"C:\SRM_ADSI\08_branding"

SUBFOLDERS = [
    "palettes",
    "logos_optimized",
    "backgrounds",
    "landings"
]

def main():
    print("\n==============================================")
    print("   SRM–QK–ADSI — BRANDING FOLDERS INIT v1")
    print("==============================================\n")

    if not os.path.exists(BASE):
        os.makedirs(BASE)
        print(f"  ✔ Creada carpeta base: {BASE}")

    for sub in SUBFOLDERS:
        path = os.path.join(BASE, sub)
        os.makedirs(path, exist_ok=True)
        print(f"  ✔ Carpeta OK → {path}")

    print("\n==============================================")
    print("   ✔ ESTRUCTURA BRANDING CREADA")
    print("   Ya puedes ejecutar palette_upgrader_v1.py")
    print("==============================================\n")

if __name__ == "__main__":
    main()
