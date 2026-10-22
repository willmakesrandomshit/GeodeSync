import os
from PIL import Image, ImageDraw, ImageFont

def make_square_thumbnail(output_path, size=1080):
    width = size
    height = size

    # 1. Base authentic GD background
    bg_path = r"C:\Program Files (x86)\Steam\steamapps\common\Geometry Dash\Resources\game_bg_01_001-uhd.png"
    if os.path.exists(bg_path):
        raw_bg = Image.open(bg_path).convert("RGBA")
        bg = raw_bg.crop((200, 200, 200 + 1600, 200 + 1600)).resize((width, height), Image.Resampling.LANCZOS)
        tint = Image.new("RGBA", (width, height), (13, 17, 28, 215))
        base = Image.alpha_composite(bg, tint)
    else:
        base = Image.new("RGBA", (width, height), (13, 17, 28, 255))

    draw_bg = ImageDraw.Draw(base)

    # 2. Lighting / Glows
    # Center purple glow
    for r in range(450, 0, -12):
        alpha = int(50 * (1 - r / 450.0))
        draw_bg.ellipse([(width // 2 - r, height // 2 - 20 - r), (width // 2 + r, height // 2 - 20 + r)], fill=(139, 92, 246, alpha))

    # Top cyan glow
    for r in range(300, 0, -15):
        alpha = int(35 * (1 - r / 300.0))
        draw_bg.ellipse([(width // 2 - r, 120 - r), (width // 2 + r, 120 + r)], fill=(56, 189, 248, alpha))

    # Bottom green glow
    for r in range(350, 0, -15):
        alpha = int(40 * (1 - r / 350.0))
        draw_bg.ellipse([(width // 2 - r, height - 200 - r), (width // 2 + r, height - 200 + r)], fill=(16, 185, 129, alpha))

    draw = ImageDraw.Draw(base)

    font_bold = "C:\\Windows\\Fonts\\bahnschrift.ttf"
    if not os.path.exists(font_bold):
        font_bold = "C:\\Windows\\Fonts\\segoeuib.ttf"

    f_top = ImageFont.truetype(font_bold, 36)
    f_main = ImageFont.truetype(font_bold, 84)
    f_title = ImageFont.truetype(font_bold, 54)
    f_card = ImageFont.truetype(font_bold, 28)
    f_btn = ImageFont.truetype(font_bold, 28)
    f_badge = ImageFont.truetype(font_bold, 20)

    def draw_bold_text(text, font, x, y, fill_color, stroke_color=(0, 0, 0), stroke_w=5, shadow_dist=6):
        draw.text((x + shadow_dist, y + shadow_dist), text, font=font, fill=(0, 0, 0, 220), stroke_width=stroke_w, stroke_fill=(0, 0, 0, 220))
        draw.text((x, y), text, font=font, fill=fill_color, stroke_width=stroke_w, stroke_fill=stroke_color)

    # 3. Top Banner: "IS YOUR GEODE BROKEN IN 2.209?"
    top_text = "IS YOUR GEODE BROKEN IN 2.209?"
    tb = draw.textbbox((0, 0), top_text, font=f_top)
    tb_w = tb[2] - tb[0]
    draw_bold_text(top_text, f_top, width // 2 - tb_w // 2, 45, (250, 204, 21), stroke_color=(20, 20, 20), stroke_w=4)

    # 4. Main Headline: "FIX IT IN 1-CLICK!"
    main_text = "FIX IT IN 1-CLICK!"
    mb = draw.textbbox((0, 0), main_text, font=f_main)
    mb_w = mb[2] - mb[0]
    draw_bold_text(main_text, f_main, width // 2 - mb_w // 2, 95, (52, 211, 153), stroke_color=(6, 78, 59), stroke_w=7)

    # 5. Big Official Geode Logo in Center
    geode_logo_path = r"C:\Users\Owner\.gemini\antigravity\scratch\gd-version-switcher\real_geode_full.png"
    if os.path.exists(geode_logo_path):
        g_img = Image.open(geode_logo_path).convert("RGBA")
        g_size = 280
        g_img = g_img.resize((g_size, g_size), Image.Resampling.LANCZOS)
        gx = width // 2 - g_size // 2
        gy = 215
        base.paste(g_img, (gx, gy), g_img)

    # 6. Brand Title below Logo: "GEODESYNC v1.1.1"
    brand_text = "⚡ GEODESYNC v1.1.1"
    brb = draw.textbbox((0, 0), brand_text, font=f_title)
    br_w = brb[2] - brb[0]
    draw_bold_text(brand_text, f_title, width // 2 - br_w // 2, 515, (255, 255, 255), stroke_color=(15, 23, 42), stroke_w=4)

    # 7. Version Comparison Badges: 2.209 ➔ 2.2081
    badges_y = 600
    b_w = 230
    b_h = 75
    gap = 40
    total_w = b_w * 2 + 50 + gap
    start_x = width // 2 - total_w // 2

    # Red 2.209
    draw.rounded_rectangle([start_x, badges_y, start_x + b_w, badges_y + b_h], radius=14, fill=(127, 29, 29, 230), outline=(239, 68, 68), width=3)
    draw_bold_text("❌ 2.209", f_card, start_x + 45, badges_y + 10, (254, 202, 202), stroke_color=(69, 10, 10), stroke_w=2)
    draw.text((start_x + 48, badges_y + 44), "MODS CRASH", font=f_badge, fill=(252, 165, 165))

    # Arrow
    draw_bold_text("➔", f_title, start_x + b_w + 15, badges_y + 12, (255, 255, 255), stroke_color=(0, 0, 0), stroke_w=4)

    # Green 2.2081
    g_start_x = start_x + b_w + 65
    draw.rounded_rectangle([g_start_x, badges_y, g_start_x + b_w, badges_y + b_h], radius=14, fill=(6, 78, 59, 230), outline=(16, 185, 129), width=3)
    draw_bold_text("✓ 2.2081", f_card, g_start_x + 40, badges_y + 10, (167, 243, 208), stroke_color=(6, 78, 59), stroke_w=2)
    draw.text((g_start_x + 36, badges_y + 44), "MODS FIXED!", font=f_badge, fill=(110, 231, 183))

    # 8. Big 1-Click Action Button
    btn_w = 700
    btn_h = 78
    btn_x = width // 2 - btn_w // 2
    btn_y = 715
    draw.rounded_rectangle([btn_x + 4, btn_y + 4, btn_x + btn_w + 4, btn_y + btn_h + 4], radius=16, fill=(0, 0, 0, 150))
    draw.rounded_rectangle([btn_x, btn_y, btn_x + btn_w, btn_y + btn_h], radius=16, fill=(139, 92, 246), outline=(196, 181, 253), width=3)
    btn_text = "⚡ 1-Click Fix: Auto-Downgrade"
    bb = draw.textbbox((0, 0), btn_text, font=f_btn)
    bb_w = bb[2] - bb[0]
    draw_bold_text(btn_text, f_btn, width // 2 - bb_w // 2, btn_y + btn_h // 2 - 16, (255, 255, 255), stroke_color=(91, 33, 182), stroke_w=3)

    # 9. Features Checklist
    feat_y = 825
    feats = [
        "🔒 Auto-Locks Steam Manifest (Blocks updates)",
        "💾 Safe Save Backup • Zero Icon or Progress Loss",
        "🛡️ 100% Free & Open Source on GitHub"
    ]
    for i, f in enumerate(feats):
        draw.text((width // 2 - 280, feat_y + i * 38), f, font=f_badge, fill=(226, 232, 240))

    # 10. Bottom Link
    bot_y = height - 55
    bot_text = "github.com/willmakesrandomshit/GeodeSync"
    bt = draw.textbbox((0, 0), bot_text, font=f_badge)
    draw_bold_text(bot_text, f_badge, width // 2 - (bt[2] - bt[0]) // 2, bot_y, (148, 163, 184), stroke_color=(0, 0, 0), stroke_w=2)

    base.save(output_path, "PNG")
    print(f"Created 1:1 Thumbnail: {output_path} ({width}x{height})")

if __name__ == "__main__":
    assets_dir = r"C:\Users\Owner\.gemini\antigravity\scratch\gd-version-switcher\assets"
    os.makedirs(assets_dir, exist_ok=True)

    out_square = os.path.join(assets_dir, "thumbnail_square.png")
    make_square_thumbnail(out_square, size=1080)

    # Save to Downloads
    dl_square = r"C:\Users\Owner\Downloads\GeodeSync-Thumbnail-1x1.png"
    make_square_thumbnail(dl_square, size=1080)
