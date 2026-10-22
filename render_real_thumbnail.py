import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def make_real_thumbnail(output_path, width=1280, height=720, is_banner=False):
    # 1. Base authentic GD background
    bg_path = r"C:\Program Files (x86)\Steam\steamapps\common\Geometry Dash\Resources\game_bg_01_001-uhd.png"
    if os.path.exists(bg_path):
        raw_bg = Image.open(bg_path).convert("RGBA")
        # Crop and resize to target
        bg = raw_bg.crop((0, 400, 2048, 400 + int(2048 * (height / width)))).resize((width, height), Image.Resampling.LANCZOS)
        # Tint with deep cyberpunk navy/purple
        tint = Image.new("RGBA", (width, height), (13, 17, 28, 210))
        base = Image.alpha_composite(bg, tint)
    else:
        base = Image.new("RGBA", (width, height), (13, 17, 28, 255))

    draw_bg = ImageDraw.Draw(base)

    # 2. Lighting / Glows
    # Left purple glow behind Geode
    for r in range(350, 0, -12):
        alpha = int(55 * (1 - r / 350.0))
        draw_bg.ellipse([(240 - r, height // 2 - r), (240 + r, height // 2 + r)], fill=(139, 92, 246, alpha))

    # Right green glow behind App UI
    for r in range(380, 0, -12):
        alpha = int(45 * (1 - r / 380.0))
        draw_bg.ellipse([(width - 320 - r, height // 2 + 40 - r), (width - 320 + r, height // 2 + 40 + r)], fill=(16, 185, 129, alpha))

    # Center top cyan glow behind headline
    for r in range(300, 0, -15):
        alpha = int(35 * (1 - r / 300.0))
        draw_bg.ellipse([(width // 2 - r, 100 - r), (width // 2 + r, 100 + r)], fill=(56, 189, 248, alpha))

    draw = ImageDraw.Draw(base)

    # Fonts
    font_bold = "C:\\Windows\\Fonts\\bahnschrift.ttf"
    if not os.path.exists(font_bold):
        font_bold = "C:\\Windows\\Fonts\\segoeuib.ttf"

    f_top = ImageFont.truetype(font_bold, 34 if not is_banner else 28)
    f_main = ImageFont.truetype(font_bold, 86 if not is_banner else 72)
    f_card = ImageFont.truetype(font_bold, 24 if not is_banner else 20)
    f_btn = ImageFont.truetype(font_bold, 22 if not is_banner else 18)
    f_badge = ImageFont.truetype(font_bold, 18 if not is_banner else 16)

    # Helper for outlined text with drop shadow
    def draw_bold_text(text, font, x, y, fill_color, stroke_color=(0, 0, 0), stroke_w=5, shadow_dist=6):
        # Shadow
        draw.text((x + shadow_dist, y + shadow_dist), text, font=font, fill=(0, 0, 0, 220), stroke_width=stroke_w, stroke_fill=(0, 0, 0, 220))
        # Stroke + Fill
        draw.text((x, y), text, font=font, fill=fill_color, stroke_width=stroke_w, stroke_fill=stroke_color)

    # 3. Top Banner Text: "IS YOUR GEODE BROKEN IN 2.209?"
    top_text = "IS YOUR GEODE BROKEN IN 2.209?"
    tb = draw.textbbox((0, 0), top_text, font=f_top)
    tb_w = tb[2] - tb[0]
    draw_bold_text(top_text, f_top, width // 2 - tb_w // 2, 38 if not is_banner else 25, (250, 204, 21), stroke_color=(20, 20, 20), stroke_w=4)

    # 4. Main Headline: "FIX IT IN 1-CLICK!"
    main_text = "FIX IT IN 1-CLICK!"
    mb = draw.textbbox((0, 0), main_text, font=f_main)
    mb_w = mb[2] - mb[0]
    draw_bold_text(main_text, f_main, width // 2 - mb_w // 2, 85 if not is_banner else 68, (52, 211, 153), stroke_color=(6, 78, 59), stroke_w=6)

    # Sub-tag: "GEODESYNC v1.1.1"
    sub_title = "⚡ GEODESYNC • 2.209 ➔ 2.2081 AUTO-DOWNGRADE"
    stb = draw.textbbox((0, 0), sub_title, font=f_card)
    st_w = stb[2] - stb[0]
    draw_bold_text(sub_title, f_card, width // 2 - st_w // 2, 188 if not is_banner else 155, (226, 232, 240), stroke_color=(15, 23, 42), stroke_w=3)

    # 5. Left Side: Real Geode Logo + Version Badges
    geode_logo_path = r"C:\Users\Owner\.gemini\antigravity\scratch\gd-version-switcher\real_geode_full.png"
    if os.path.exists(geode_logo_path):
        g_img = Image.open(geode_logo_path).convert("RGBA")
        g_size = 230 if not is_banner else 190
        g_img = g_img.resize((g_size, g_size), Image.Resampling.LANCZOS)
        
        # Glow ring around Geode
        gx = 110
        gy = 265 if not is_banner else 225
        base.paste(g_img, (gx, gy), g_img)

        # "GEODE MODS" label below logo
        g_lbl = "GEODE MODS"
        glb = draw.textbbox((0, 0), g_lbl, font=f_card)
        draw_bold_text(g_lbl, f_card, gx + g_size // 2 - (glb[2] - glb[0]) // 2, gy + g_size + 10, (196, 181, 253), stroke_color=(15, 23, 42), stroke_w=3)

    # 6. Badges: 2.209 (Broken) -> 2.2081 (Working)
    # Red 2.209 badge
    red_x = 370
    red_y = 295 if not is_banner else 250
    draw.rounded_rectangle([red_x, red_y, red_x + 190, red_y + 60], radius=12, fill=(127, 29, 29, 230), outline=(239, 68, 68), width=3)
    draw_bold_text("❌ 2.209", f_card, red_x + 35, red_y + 14, (254, 202, 202), stroke_color=(69, 10, 10), stroke_w=2)
    draw.text((red_x + 35, red_y + 40), "MODS BROKEN", font=f_badge, fill=(252, 165, 165))

    # Arrow
    draw_bold_text("➔", f_main, red_x + 80, red_y + 70, (255, 255, 255), stroke_color=(0, 0, 0), stroke_w=4)

    # Green 2.2081 badge
    green_y = red_y + 155 if not is_banner else red_y + 130
    draw.rounded_rectangle([red_x, green_y, red_x + 190, green_y + 60], radius=12, fill=(6, 78, 59, 230), outline=(16, 185, 129), width=3)
    draw_bold_text("✓ 2.2081", f_card, red_x + 32, green_y + 14, (167, 243, 208), stroke_color=(6, 78, 59), stroke_w=2)
    draw.text((red_x + 32, green_y + 40), "MODS WORKING!", font=f_badge, fill=(110, 231, 183))

    # 7. Right Side: Authentic GeodeSync UI Mockup Card
    cx = 630
    cy = 260 if not is_banner else 225
    cw = 580
    ch = 345 if not is_banner else 295

    # Card shadow
    draw.rounded_rectangle([cx + 6, cy + 6, cx + cw + 6, cy + ch + 6], radius=18, fill=(0, 0, 0, 140))
    # Card base
    draw.rounded_rectangle([cx, cy, cx + cw, cy + ch], radius=18, fill=(22, 30, 46, 245), outline=(59, 130, 246), width=3)

    # Card Top Header
    draw.rounded_rectangle([cx, cy, cx + cw, cy + 50], radius=18, fill=(15, 23, 42, 255), outline=(59, 130, 246), width=1)
    # macOS/Windows window dots
    draw.ellipse([cx + 18, cy + 18, cx + 32, cy + 32], fill=(239, 68, 68))
    draw.ellipse([cx + 40, cy + 18, cx + 54, cy + 32], fill=(245, 158, 11))
    draw.ellipse([cx + 62, cy + 18, cx + 76, cy + 32], fill=(16, 185, 129))
    draw.text((cx + 95, cy + 15), "GeodeSync v1.1.1 • Automated Fix", font=f_badge, fill=(148, 163, 184))

    # Card Body Content
    draw.text((cx + 25, cy + 65), "AUTOMATED 1-CLICK FIX READY", font=f_badge, fill=(192, 132, 252))
    draw_bold_text("⚡ Automatic Downgrade & Protect", f_card, cx + 25, cy + 90, (255, 255, 255), stroke_color=(15, 23, 42), stroke_w=2)

    # The Big Highlighted Button (Exact match of the real app!)
    btn_y = cy + 140 if not is_banner else cy + 130
    btn_h = 60 if not is_banner else 52
    draw.rounded_rectangle([cx + 25, btn_y, cx + cw - 25, btn_y + btn_h], radius=12, fill=(139, 92, 246), outline=(196, 181, 253), width=2)
    btn_text = "⚡ 1-Click Fix: Auto-Download & Downgrade to 2.2081"
    bb = draw.textbbox((0, 0), btn_text, font=f_btn)
    bb_w = bb[2] - bb[0]
    draw_bold_text(btn_text, f_btn, cx + 25 + (cw - 50) // 2 - bb_w // 2, btn_y + btn_h // 2 - 12, (255, 255, 255), stroke_color=(91, 33, 182), stroke_w=3)

    # Features below button
    fx_y = btn_y + btn_h + 20
    draw.text((cx + 35, fx_y), "🔒 Auto-Locks Steam Manifest (Blocks unwanted updates)", font=f_badge, fill=(52, 211, 153))
    draw.text((cx + 35, fx_y + 26), "💾 Safe Save Backup • Zero Icon or Progress Loss", font=f_badge, fill=(56, 189, 248))
    draw.text((cx + 35, fx_y + 52), "🔄 1-Click Restore to Latest when Geode updates", font=f_badge, fill=(251, 191, 36))

    # 8. Bottom Bar: Real Open-Source GitHub Link & Tags
    bottom_y = height - 42 if not is_banner else height - 32
    b_tag = "100% FREE & OPEN SOURCE • GITHUB.COM/WILLMAKESRANDOMSHIT/GEODESYNC"
    btb = draw.textbbox((0, 0), b_tag, font=f_badge)
    draw_bold_text(b_tag, f_badge, width // 2 - (btb[2] - btb[0]) // 2, bottom_y, (148, 163, 184), stroke_color=(0, 0, 0), stroke_w=2)

    base.save(output_path, "PNG")
    print(f"Created: {output_path} ({width}x{height})")

if __name__ == "__main__":
    assets_dir = r"C:\Users\Owner\.gemini\antigravity\scratch\gd-version-switcher\assets"
    os.makedirs(assets_dir, exist_ok=True)
    
    # 1. 16:9 YouTube / TikTok Thumbnail (1280x720)
    thumb_path = os.path.join(assets_dir, "thumbnail.png")
    make_real_thumbnail(thumb_path, 1280, 720, is_banner=False)

    # 2. 2:1 GitHub Social Preview Banner (1280x640)
    banner_path = os.path.join(assets_dir, "banner.png")
    make_real_thumbnail(banner_path, 1280, 640, is_banner=True)

    # 3. Copy to Downloads for user
    dl_dir = r"C:\Users\Owner\Downloads"
    make_real_thumbnail(os.path.join(dl_dir, "GeodeSync-Thumbnail.png"), 1280, 720, is_banner=False)
    make_real_thumbnail(os.path.join(dl_dir, "GeodeSync-Banner.png"), 1280, 640, is_banner=True)
