from PIL import Image

sheet_path = r"C:\Program Files (x86)\Steam\steamapps\common\Geometry Dash\geode\resources\geode.loader\LogoSheet-uhd.png"
sheet = Image.open(sheet_path)

# geode.loader/geode-logo-color.png {{456,0},{228,229}}
# Rect: x=456, y=0, w=228, h=229
logo_color = sheet.crop((456, 0, 456 + 228, 0 + 229))
logo_color.save(r"C:\Users\Owner\.gemini\antigravity\scratch\gd-version-switcher\real_geode_logo.png")

# geode.loader/geode-logo.png {{0,326},{324,324}}
logo_full = sheet.crop((0, 326, 324, 326 + 324))
logo_full.save(r"C:\Users\Owner\.gemini\antigravity\scratch\gd-version-switcher\real_geode_full.png")

print("Saved real Geode logos successfully!")
