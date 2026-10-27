"""Build the Windows icon from the shared GeodeSync brand asset."""
from pathlib import Path
from PIL import Image


def create_geode_icon(output_path):
    source = Path(__file__).resolve().parent / "assets" / "geodesync-app-icon.png"
    with Image.open(source) as image:
        image.save(output_path, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    create_geode_icon("icon.ico")
