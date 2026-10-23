import os
import math
from PIL import Image, ImageDraw, ImageFont

def draw_arrow_down(draw, cx, cy, size=24, color=(255, 255, 255)):
    # Draw downward arrow polygon
    w = size
    h = size * 1.2
    # points: top shaft, head
    sw = w * 0.35
    sh = h * 0.45
    pts = [
        (cx - sw // 2, cy - h // 2),
        (cx + sw // 2, cy - h // 2),
        (cx + sw // 2, cy - h // 2 + sh),
        (cx + w // 2, cy - h // 2 + sh),
        (cx, cy + h // 2),
        (cx - w // 2, cy - h // 2 + sh),
        (cx - sw // 2, cy - h // 2 + sh),
    ]
    draw.polygon(pts, fill=color)

def draw_arrow_right(draw, cx, cy, size=28, color=(255, 255, 255)):
    # Draw rightward arrow polygon
    w = size * 1.2
    h = size
    sw = h * 0.35
    pts = [
        (cx - w // 2, cy - sw // 2),
        (cx + w // 2 - h // 2, cy - sw // 2),
        (cx + w // 2 - h // 2, cy - h // 2),
        (cx + w // 2, cy),
        (cx + w // 2 - h // 2, cy + h // 2),
        (cx + w // 2 - h // 2, cy + sw // 2),
        (cx - w // 2, cy + sw // 2)
    ]
    draw.polygon(pts, fill=color)

def draw_lightning(draw, cx, cy, size=20, color=(250, 204, 21)):
    # Points for a crisp lightning bolt
    w = size
    h = size * 1.3
    pts = [
        (cx + w * 0.1, cy - h * 0.5),
        (cx - w * 0.45, cy + h * 0.05),
        (cx - w * 0.05, cy + h * 0.05),
        (cx - w * 0.25, cy + h * 0.5),
        (cx + w * 0.45, cy - h * 0.05),
        (cx + w * 0.05, cy - h * 0.05),
    ]
    draw.polygon(pts, fill=color)

def render_banner_and_thumb(output_path, width=1280, height=720, is_banner=False):
    bg_path = r"C:\Program Files (x86)\Steam\steamapps\common\Geometry Dash\Resources\game_bg_01_001-uhd.png"
    if os.path.exists(bg_path):
        raw_bg = Image.open(bg_path).convert("RGBA")
        crop_h = int(2048 * (height / width))
        bg = raw_bg.crop((0, 380, 2048, 380 + crop_h)).resize((width, height), Image.Resampling.LANCZOS)
        tint = Image.new("RGBA", (width, height), (13, 17, 28, 215))
        base = Image.alpha_composite(bg, tint)
    else:
        base = Image.new("RGBA", (width, height), (13, 17, 28, 255))

    draw_bg = ImageDraw.Draw(base)

    # Glows
    for r in range(360, 0, -12):
        alpha = int(55 * (1 - r / 360.0))
        draw_bg.ellipse([(230 - r, height // 2 - r), (230 + r, height // 2 + r)], fill=(139, 92, 246, alpha))

    for r in range(400, 0, -12):
        alpha = int(45 * (1 - r / 400.0))
        draw_bg.ellipse([(width - 320 - r, height // 2 + 30 - r), (width - 320 + r, height // 2 + 30 + r)], fill=(16, 185, 129, alpha))

    for r in range(320, 0, -15):
        alpha = int(40 * (1 - r / 320.0))
        draw_bg.ellipse([(width // 2 - r, 90 - r), (width // 2 + r, 90 + r)], fill=(56, 189, 248, alpha))

    draw = ImageDraw.Draw(base)

    font_path = "C:\\Windows\\Fonts\\bahnschrift.ttf"
    if not os.path.exists(font_path):
        font_path = "C:\\Windows\\Fonts\\segoeuib.ttf"

    f_top = ImageFont.truetype(font_path, 32 if not is_banner else 26)
    f_main = ImageFont.truetype(font_path, 84 if not is_banner else 70)
    f_sub = ImageFont.truetype(font_path, 22 if not is_banner else 19)
    f_card_title = ImageFont.truetype(font_path, 24 if not is_banner else 20)
    f_btn = ImageFont.truetype(font_path, 21 if not is_banner else 18)
    f_item = ImageFont.truetype(font_path, 17 if not is_banner else 15)
    f_badge_bold = ImageFont.truetype(font_path, 22 if not is_banner else 19)
    f_badge_sub = ImageFont.truetype(font_path, 15 if not is_banner else 13)

    def draw_bold(text, font, x, y, fill_color, stroke_color=(0, 0, 0), stroke_w=4, shadow_dist=5):
        draw.text((x + shadow_dist, y + shadow_dist), text, font=font, fill=(0, 0, 0, 200), stroke_width=stroke_w, stroke_fill=(0, 0, 0, 200))
        draw.text((x, y), text, font=font, fill=fill_color, stroke_width=stroke_w, stroke_fill=stroke_color)

    # 1. Top Question: "IS YOUR GEODE BROKEN IN 2.209?"
    top_txt = "IS YOUR GEODE BROKEN IN 2.209?"
    tb = draw.textbbox((0, 0), top_txt, font=f_top)
    tb_w = tb[2] - tb[0]
    top_y = 35 if not is_banner else 22
    draw_bold(top_txt, f_top, width // 2 - tb_w // 2, top_y, (250, 204, 21), stroke_color=(20, 20, 20), stroke_w=4)

    # 2. Main Headline: "FIX IT IN 1-CLICK!"
    main_txt = "FIX IT IN 1-CLICK!"
    mb = draw.textbbox((0, 0), main_txt, font=f_main)
    mb_w = mb[2] - mb[0]
    main_y = 80 if not is_banner else 62
    draw_bold(main_txt, f_main, width // 2 - mb_w // 2, main_y, (52, 211, 153), stroke_color=(6, 78, 59), stroke_w=6)

    # 3. Sub-bar: "GEODESYNC v1.1.3  •  2.209 >> 2.2081 AUTO-DOWNGRADE"
    sub_txt = "GEODESYNC v1.1.3   |   2.209 >> 2.2081 AUTO-DOWNGRADE"
    sb = draw.textbbox((0, 0), sub_txt, font=f_sub)
    sb_w = sb[2] - sb[0]
    sub_y = 180 if not is_banner else 146
    # draw lightning icon next to it
    draw_lightning(draw, width // 2 - sb_w // 2 - 16, sub_y + 12, size=18, color=(250, 204, 21))
    draw_bold(sub_txt, f_sub, width // 2 - sb_w // 2 + 8, sub_y, (226, 232, 240), stroke_color=(15, 23, 42), stroke_w=3)

    # 4. Left side: Geode official logo
    geode_logo_path = r"C:\Users\Owner\.gemini\antigravity\scratch\gd-version-switcher\real_geode_full.png"
    if os.path.exists(geode_logo_path):
        g_img = Image.open(geode_logo_path).convert("RGBA")
        g_size = 220 if not is_banner else 180
        g_img = g_img.resize((g_size, g_size), Image.Resampling.LANCZOS)
        gx = 95
        gy = 250 if not is_banner else 215
        base.paste(g_img, (gx, gy), g_img)

        g_lbl = "GEODE MODS"
        glb = draw.textbbox((0, 0), g_lbl, font=f_card_title)
        draw_bold(g_lbl, f_card_title, gx + g_size // 2 - (glb[2] - glb[0]) // 2, gy + g_size + 8, (196, 181, 253), stroke_color=(15, 23, 42), stroke_w=3)

    # 5. Middle Badges: 2.209 -> 2.2081
    badge_x = 345
    b_w = 190
    b_h = 64
    red_y = 275 if not is_banner else 235

    # Red Badge
    draw.rounded_rectangle([badge_x, red_y, badge_x + b_w, red_y + b_h], radius=12, fill=(127, 29, 29, 235), outline=(239, 68, 68), width=3)
    # Draw cross icon
    draw.line([(badge_x + 22, red_y + 18), (badge_x + 38, red_y + 34)], fill=(254, 202, 202), width=3)
    draw.line([(badge_x + 38, red_y + 18), (badge_x + 22, red_y + 34)], fill=(254, 202, 202), width=3)
    draw_bold("GD 2.209", f_badge_bold, badge_x + 48, red_y + 11, (254, 202, 202), stroke_color=(69, 10, 10), stroke_w=2)
    draw.text((badge_x + 48, red_y + 38), "MODS BROKEN", font=f_badge_sub, fill=(252, 165, 165))

    # Down Arrow
    arrow_cy = red_y + b_h + 35 if not is_banner else red_y + b_h + 26
    draw_arrow_down(draw, badge_x + b_w // 2, arrow_cy, size=28, color=(255, 255, 255))

    # Green Badge
    green_y = red_y + b_h + 70 if not is_banner else red_y + b_h + 52
    draw.rounded_rectangle([badge_x, green_y, badge_x + b_w, green_y + b_h], radius=12, fill=(6, 78, 59, 235), outline=(16, 185, 129), width=3)
    # Draw checkmark icon
    draw.line([(badge_x + 20, green_y + 26), (badge_x + 28, green_y + 34)], fill=(167, 243, 208), width=3)
    draw.line([(badge_x + 28, green_y + 34), (badge_x + 40, green_y + 18)], fill=(167, 243, 208), width=3)
    draw_bold("GD 2.2081", f_badge_bold, badge_x + 48, green_y + 11, (167, 243, 208), stroke_color=(6, 78, 59), stroke_w=2)
    draw.text((badge_x + 48, green_y + 38), "MODS WORKING!", font=f_badge_sub, fill=(110, 231, 183))

    # 6. Right Side: GeodeSync v1.1.2 Pro Power Suite Mockup
    cx = 585
    cy = 245 if not is_banner else 210
    cw = 615
    ch = 385 if not is_banner else 335

    # Shadow
    draw.rounded_rectangle([cx + 6, cy + 6, cx + cw + 6, cy + ch + 6], radius=16, fill=(0, 0, 0, 160))
    # Card base
    draw.rounded_rectangle([cx, cy, cx + cw, cy + ch], radius=16, fill=(22, 30, 46, 250), outline=(59, 130, 246), width=3)

    # Card Top Header
    header_h = 42 if not is_banner else 36
    draw.rounded_rectangle([cx, cy, cx + cw, cy + header_h], radius=16, fill=(15, 23, 42, 255), outline=(59, 130, 246), width=1)
    draw.rectangle([cx, cy + 20, cx + cw, cy + header_h], fill=(15, 23, 42, 255)) # flatten bottom corners of header
    # dots
    draw.ellipse([cx + 16, cy + 13, cx + 28, cy + 25], fill=(239, 68, 68))
    draw.ellipse([cx + 36, cy + 13, cx + 48, cy + 25], fill=(245, 158, 11))
    draw.ellipse([cx + 56, cy + 13, cx + 68, cy + 25], fill=(16, 185, 129))
    draw.text((cx + 86, cy + 10), "GeodeSync v1.1.3 • Power & Performance Suite", font=f_item, fill=(148, 163, 184))

    # Card Content
    draw.text((cx + 24, cy + header_h + 12), "AUTOMATED 1-CLICK FIX READY", font=f_badge_sub, fill=(192, 132, 252))
    draw_bold("Automatic Downgrade & Steam Protect", f_card_title, cx + 24, cy + header_h + 30, (255, 255, 255), stroke_color=(15, 23, 42), stroke_w=2)

    # The Big Highlighted Button
    btn_y = cy + header_h + 74 if not is_banner else cy + header_h + 65
    btn_h = 54 if not is_banner else 46
    draw.rounded_rectangle([cx + 24, btn_y, cx + cw - 24, btn_y + btn_h], radius=10, fill=(139, 92, 246), outline=(196, 181, 253), width=2)
    btn_txt = "1-Click Fix: Auto-Download & Downgrade to 2.2081"
    bb = draw.textbbox((0, 0), btn_txt, font=f_btn)
    bb_w = bb[2] - bb[0]
    draw_lightning(draw, cx + 24 + (cw - 48) // 2 - bb_w // 2 - 14, btn_y + btn_h // 2, size=16, color=(255, 255, 255))
    draw_bold(btn_txt, f_btn, cx + 24 + (cw - 48) // 2 - bb_w // 2 + 10, btn_y + btn_h // 2 - 12, (255, 255, 255), stroke_color=(91, 33, 182), stroke_w=3)

    # Power Features list below button
    features = [
        ("Fix Click Delay: 128 FMOD WASAPI Low-Latency & CBF Mouse Fix", (52, 211, 153)),
        ("FPS Unlocker: 144 / 240 / 360 / 480 FPS Direct Save Target", (56, 189, 248)),
        ("Save Doctor: Auto-Repairs Corrupted Saves & Lost Progress", (167, 139, 250)),
        ("NONG Songs: 1-Click Custom Music & 3GB+ Cache Cleaner", (251, 191, 36))
    ]

    fy = btn_y + btn_h + 16 if not is_banner else btn_y + btn_h + 12
    step_y = 26 if not is_banner else 23
    for i, (feat, col) in enumerate(features):
        cur_y = fy + i * step_y
        # Bullet circle
        draw.ellipse([cx + 26, cur_y + 4, cx + 34, cur_y + 12], fill=col)
        draw.text((cx + 42, cur_y), feat, font=f_item, fill=col)

    # 7. Bottom Bar
    bottom_y = height - 36 if not is_banner else height - 26
    b_tag = "100% FREE & OPEN SOURCE • GITHUB.COM/WILLMAKESRANDOMSHIT/GEODESYNC"
    btb = draw.textbbox((0, 0), b_tag, font=f_item)
    draw_bold(b_tag, f_item, width // 2 - (btb[2] - btb[0]) // 2, bottom_y, (148, 163, 184), stroke_color=(0, 0, 0), stroke_w=2)

    base.save(output_path, "PNG")
    print(f"Created: {output_path} ({width}x{height})")


def render_square_thumbnail(output_path, size=1080):
    width = size
    height = size

    bg_path = r"C:\Program Files (x86)\Steam\steamapps\common\Geometry Dash\Resources\game_bg_01_001-uhd.png"
    if os.path.exists(bg_path):
        raw_bg = Image.open(bg_path).convert("RGBA")
        bg = raw_bg.crop((200, 200, 200 + 1600, 200 + 1600)).resize((width, height), Image.Resampling.LANCZOS)
        tint = Image.new("RGBA", (width, height), (13, 17, 28, 215))
        base = Image.alpha_composite(bg, tint)
    else:
        base = Image.new("RGBA", (width, height), (13, 17, 28, 255))

    draw_bg = ImageDraw.Draw(base)

    for r in range(450, 0, -12):
        alpha = int(50 * (1 - r / 450.0))
        draw_bg.ellipse([(width // 2 - r, height // 2 - 30 - r), (width // 2 + r, height // 2 - 30 + r)], fill=(139, 92, 246, alpha))

    for r in range(320, 0, -15):
        alpha = int(40 * (1 - r / 320.0))
        draw_bg.ellipse([(width // 2 - r, 110 - r), (width // 2 + r, 110 + r)], fill=(56, 189, 248, alpha))

    for r in range(350, 0, -15):
        alpha = int(40 * (1 - r / 350.0))
        draw_bg.ellipse([(width // 2 - r, height - 180 - r), (width // 2 + r, height - 180 + r)], fill=(16, 185, 129, alpha))

    draw = ImageDraw.Draw(base)

    font_path = "C:\\Windows\\Fonts\\bahnschrift.ttf"
    if not os.path.exists(font_path):
        font_path = "C:\\Windows\\Fonts\\segoeuib.ttf"

    f_top = ImageFont.truetype(font_path, 34)
    f_main = ImageFont.truetype(font_path, 80)
    f_title = ImageFont.truetype(font_path, 48)
    f_badge_bold = ImageFont.truetype(font_path, 28)
    f_badge_sub = ImageFont.truetype(font_path, 18)
    f_pill = ImageFont.truetype(font_path, 20)
    f_tag = ImageFont.truetype(font_path, 18)

    def draw_bold(text, font, x, y, fill_color, stroke_color=(0, 0, 0), stroke_w=4, shadow_dist=5):
        draw.text((x + shadow_dist, y + shadow_dist), text, font=font, fill=(0, 0, 0, 200), stroke_width=stroke_w, stroke_fill=(0, 0, 0, 200))
        draw.text((x, y), text, font=font, fill=fill_color, stroke_width=stroke_w, stroke_fill=stroke_color)

    # 1. Top Question
    top_txt = "IS YOUR GEODE BROKEN IN 2.209?"
    tb = draw.textbbox((0, 0), top_txt, font=f_top)
    tb_w = tb[2] - tb[0]
    draw_bold(top_txt, f_top, width // 2 - tb_w // 2, 42, (250, 204, 21), stroke_color=(20, 20, 20), stroke_w=4)

    # 2. Main Title
    main_txt = "FIX IT IN 1-CLICK!"
    mb = draw.textbbox((0, 0), main_txt, font=f_main)
    mb_w = mb[2] - mb[0]
    draw_bold(main_txt, f_main, width // 2 - mb_w // 2, 88, (52, 211, 153), stroke_color=(6, 78, 59), stroke_w=6)

    # 3. Big Official Geode Logo
    geode_logo_path = r"C:\Users\Owner\.gemini\antigravity\scratch\gd-version-switcher\real_geode_full.png"
    if os.path.exists(geode_logo_path):
        g_img = Image.open(geode_logo_path).convert("RGBA")
        g_size = 280
        g_img = g_img.resize((g_size, g_size), Image.Resampling.LANCZOS)
        gx = width // 2 - g_size // 2
        gy = 200
        base.paste(g_img, (gx, gy), g_img)

    # 4. Brand Name: GEODESYNC v1.1.3
    brand_txt = "GEODESYNC v1.1.3"
    brb = draw.textbbox((0, 0), brand_txt, font=f_title)
    br_w = brb[2] - brb[0]
    draw_lightning(draw, width // 2 - br_w // 2 - 24, 518, size=24, color=(250, 204, 21))
    draw_bold(brand_txt, f_title, width // 2 - br_w // 2 + 10, 498, (255, 255, 255), stroke_color=(15, 23, 42), stroke_w=4)

    # 5. Version comparison badges
    badges_y = 580
    b_w = 230
    b_h = 76
    gap = 40
    total_w = b_w * 2 + 50 + gap
    start_x = width // 2 - total_w // 2

    # Red 2.209
    draw.rounded_rectangle([start_x, badges_y, start_x + b_w, badges_y + b_h], radius=14, fill=(127, 29, 29, 235), outline=(239, 68, 68), width=3)
    draw.line([(start_x + 22, badges_y + 22), (start_x + 38, badges_y + 38)], fill=(254, 202, 202), width=3)
    draw.line([(start_x + 38, badges_y + 22), (start_x + 22, badges_y + 38)], fill=(254, 202, 202), width=3)
    draw_bold("GD 2.209", f_badge_bold, start_x + 48, badges_y + 12, (254, 202, 202), stroke_color=(69, 10, 10), stroke_w=2)
    draw.text((start_x + 48, badges_y + 44), "MODS BROKEN", font=f_badge_sub, fill=(252, 165, 165))

    # Right Arrow
    draw_arrow_right(draw, start_x + b_w + 35, badges_y + b_h // 2, size=32, color=(255, 255, 255))

    # Green 2.2081
    g_start_x = start_x + b_w + 70
    draw.rounded_rectangle([g_start_x, badges_y, g_start_x + b_w, badges_y + b_h], radius=14, fill=(6, 78, 59, 235), outline=(16, 185, 129), width=3)
    draw.line([(g_start_x + 20, badges_y + 30), (g_start_x + 28, badges_y + 38)], fill=(167, 243, 208), width=3)
    draw.line([(g_start_x + 28, badges_y + 38), (g_start_x + 40, badges_y + 22)], fill=(167, 243, 208), width=3)
    draw_bold("GD 2.2081", f_badge_bold, g_start_x + 48, badges_y + 12, (167, 243, 208), stroke_color=(6, 78, 59), stroke_w=2)
    draw.text((g_start_x + 48, badges_y + 44), "MODS WORKING!", font=f_badge_sub, fill=(110, 231, 183))

    # 6. Feature List
    py = 680
    card_w = 560
    card_h = 205
    card_x = width // 2 - card_w // 2
    draw.rounded_rectangle([card_x, py, card_x + card_w, py + card_h], radius=16, fill=(22, 30, 46, 240), outline=(59, 130, 246), width=2)
    
    draw.text((card_x + 24, py + 16), "POWER & PERFORMANCE SUITE:", font=f_badge_sub, fill=(148, 163, 184))

    feats_list = [
        ("Fix Click Delay: FMOD 128 WASAPI buffer (~2.7ms)", (52, 211, 153)),
        ("Save Doctor: Auto-recovers lost stars and icons", (167, 139, 250)),
        ("Crash Doctor: 1-Click faulty mod disabler", (56, 189, 248)),
        ("Cache Cleaner: Safely frees 3GB+ audio files", (251, 191, 36)),
        ("Steam Depot: Live download progress & size tracker", (226, 232, 240))
    ]
    for i, (txt, col) in enumerate(feats_list):
        cur_y = py + 44 + i * 28
        draw.ellipse([card_x + 24, cur_y + 4, card_x + 32, cur_y + 12], fill=col)
        draw.text((card_x + 42, cur_y), txt, font=f_tag, fill=col)

    # 7. Big 1-Click Action Button at bottom
    btn_w = 640
    btn_h = 68
    bx = width // 2 - btn_w // 2
    by = 910
    draw.rounded_rectangle([bx, by, bx + btn_w, by + btn_h], radius=14, fill=(139, 92, 246), outline=(196, 181, 253), width=2)
    b_txt = "1-Click Auto-Downgrade & Steam Lock"
    bb = draw.textbbox((0, 0), b_txt, font=f_pill)
    bb_w = bb[2] - bb[0]
    draw_lightning(draw, width // 2 - bb_w // 2 - 16, by + btn_h // 2, size=20, color=(255, 255, 255))
    draw_bold(b_txt, f_pill, width // 2 - bb_w // 2 + 10, by + btn_h // 2 - 12, (255, 255, 255), stroke_color=(91, 33, 182), stroke_w=3)

    # 8. Footer
    bot_y = height - 45
    draw_bold("100% FREE & OPEN SOURCE • GITHUB.COM/WILLMAKESRANDOMSHIT/GEODESYNC", f_tag, width // 2 - 310, bot_y, (148, 163, 184), stroke_color=(0, 0, 0), stroke_w=2)

    base.save(output_path, "PNG")
    print(f"Created Square Thumbnail: {output_path} ({width}x{height})")


if __name__ == "__main__":
    assets_dir = r"C:\Users\Owner\.gemini\antigravity\scratch\gd-version-switcher\assets"
    dl_dir = r"C:\Users\Owner\Downloads"
    os.makedirs(assets_dir, exist_ok=True)

    # 1. 16:9 Thumbnail (1280x720)
    render_banner_and_thumb(os.path.join(assets_dir, "thumbnail.png"), 1280, 720, is_banner=False)
    render_banner_and_thumb(os.path.join(dl_dir, "GeodeSync-Thumbnail.png"), 1280, 720, is_banner=False)

    # 2. 2:1 GitHub Banner (1280x640)
    render_banner_and_thumb(os.path.join(assets_dir, "banner.png"), 1280, 640, is_banner=True)
    render_banner_and_thumb(os.path.join(dl_dir, "GeodeSync-Banner.png"), 1280, 640, is_banner=True)

    # 3. 1:1 Square Thumbnail (1080x1080)
    render_square_thumbnail(os.path.join(assets_dir, "thumbnail_square.png"), 1080)
    render_square_thumbnail(os.path.join(dl_dir, "GeodeSync-Thumbnail-1x1.png"), 1080)
