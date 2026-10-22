import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def draw_rounded_rectangle(draw, bounds, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(bounds, radius=radius, fill=fill, outline=outline, width=width)

def draw_crystal_icon(draw, cx, cy, size):
    s = size / 256.0
    w = size
    h = size
    ox = cx - size / 2
    oy = cy - size / 2

    # Shield background
    margin = 8 * s
    draw.rounded_rectangle([ox + margin, oy + margin, ox + w - margin, oy + h - margin], radius=32 * s, fill=(22, 27, 40, 240), outline=(139, 92, 246, 255), width=max(1, int(4 * s)))

    # Crystal top facet
    p1 = (ox + w * 0.5, oy + 38 * s)
    p2 = (ox + w - 38 * s, oy + 85 * s)
    p3 = (ox + w * 0.5, oy + 138 * s)
    p4 = (ox + 38 * s, oy + 85 * s)
    draw.polygon([p1, p2, p3, p4], fill=(167, 139, 250, 255), outline=(196, 181, 253, 255))

    # Bottom left facet
    p5 = (ox + 38 * s, oy + 172 * s)
    p6 = (ox + w * 0.5, oy + 222 * s)
    draw.polygon([p4, p3, p6, p5], fill=(139, 92, 246, 255), outline=(167, 139, 250, 255))

    # Bottom right facet
    p7 = (ox + w - 38 * s, oy + 172 * s)
    draw.polygon([p3, p2, p7, p6], fill=(109, 40, 217, 255), outline=(139, 92, 246, 255))

    # Electric bolt in center
    lp = [
        (ox + w * 0.53, oy + 65 * s),
        (ox + w * 0.42, oy + 125 * s),
        (ox + w * 0.51, oy + 125 * s),
        (ox + w * 0.44, oy + 188 * s),
        (ox + w * 0.62, oy + 115 * s),
        (ox + w * 0.52, oy + 115 * s),
    ]
    draw.polygon(lp, fill=(250, 204, 21, 255))

def create_geodesync_thumbnail(bg_image_path=None, output_path="thumbnail.png", width=1280, height=720):
    if bg_image_path and os.path.exists(bg_image_path):
        base = Image.open(bg_image_path).convert("RGBA").resize((width, height), Image.Resampling.LANCZOS)
        # Apply dark overlay for high contrast text readability
        overlay = Image.new("RGBA", (width, height), (15, 20, 28, 170))
        base = Image.alpha_composite(base, overlay)
    else:
        # Create dark modern gradient background
        base = Image.new("RGBA", (width, height), (15, 20, 28, 255))
        draw_bg = ImageDraw.Draw(base)
        
        # Radial glowing lights in background
        for r in range(400, 0, -10):
            alpha = int(45 * (1 - r / 400.0))
            # Purple glow on top left
            draw_bg.ellipse([(150 - r, 100 - r), (150 + r, 100 + r)], fill=(139, 92, 246, alpha))
            # Cyan glow on bottom right
            draw_bg.ellipse([(width - 200 - r, height - 150 - r), (width - 200 + r, height - 150 + r)], fill=(6, 182, 212, alpha))
            # Emerald glow center
            draw_bg.ellipse([(width // 2 - r, height // 2 - r), (width // 2 + r, height // 2 + r)], fill=(16, 185, 129, int(alpha * 0.7)))

        # Subtle grid lines
        for x in range(0, width, 60):
            draw_bg.line([(x, 0), (x, height)], fill=(255, 255, 255, 10), width=1)
        for y in range(0, height, 60):
            draw_bg.line([(0, y), (width, y)], fill=(255, 255, 255, 10), width=1)

    draw = ImageDraw.Draw(base)

    # Fonts
    font_bold = "C:\\Windows\\Fonts\\bahnschrift.ttf"
    if not os.path.exists(font_bold):
        font_bold = "C:\\Windows\\Fonts\\segoeuib.ttf"

    title_font = ImageFont.truetype(font_bold, 84)
    subtitle_font = ImageFont.truetype(font_bold, 28)
    badge_font = ImageFont.truetype(font_bold, 18)
    pill_font = ImageFont.truetype(font_bold, 22)

    # Top Tagline / Category Badge
    top_badge_text = "GEOMETRY DASH • 1-CLICK MOD FIX"
    tb_bbox = draw.textbbox((0, 0), top_badge_text, font=badge_font)
    tb_w = tb_bbox[2] - tb_bbox[0]
    tb_h = tb_bbox[3] - tb_bbox[1]
    tb_x = width // 2 - tb_w // 2
    tb_y = 65

    draw.rounded_rectangle([tb_x - 18, tb_y - 8, tb_x + tb_w + 18, tb_y + tb_h + 8], radius=16, fill=(30, 41, 59, 230), outline=(56, 189, 248, 255), width=2)
    draw.text((tb_x, tb_y - 2), top_badge_text, fill=(56, 189, 248, 255), font=badge_font)

    # Icon + Title layout
    icon_size = 130
    title_text = "GEODESYNC"
    t_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    t_w = t_bbox[2] - t_bbox[0]
    t_h = t_bbox[3] - t_bbox[1]

    total_header_w = icon_size + 24 + t_w
    header_x = width // 2 - total_header_w // 2
    header_y = 135

    # Draw Crystal Icon
    draw_crystal_icon(draw, header_x + icon_size // 2, header_y + icon_size // 2, icon_size)

    # Draw Text Drop Shadow
    draw.text((header_x + icon_size + 28, header_y + 16), title_text, fill=(0, 0, 0, 180), font=title_font)
    # Draw Title with crisp gradient look
    draw.text((header_x + icon_size + 24, header_y + 12), title_text, fill=(255, 255, 255, 255), font=title_font)

    # Version tag pill
    ver_text = "v1.1.1"
    v_bbox = draw.textbbox((0, 0), ver_text, font=badge_font)
    v_w = v_bbox[2] - v_bbox[0]
    v_x = header_x + icon_size + 24 + t_w + 16
    v_y = header_y + 24
    draw.rounded_rectangle([v_x - 10, v_y - 4, v_x + v_w + 10, v_y + 24], radius=10, fill=(16, 185, 129, 240), outline=(52, 211, 153, 255), width=1)
    draw.text((v_x, v_y), ver_text, fill=(255, 255, 255), font=badge_font)

    # Subtitle
    sub_text = "Play Geode Mods on 2.2081 • Auto-Downgrade • Protect Game Files"
    s_bbox = draw.textbbox((0, 0), sub_text, font=subtitle_font)
    s_w = s_bbox[2] - s_bbox[0]
    draw.text((width // 2 - s_w // 2, header_y + icon_size + 15), sub_text, fill=(203, 213, 225, 255), font=subtitle_font)

    # Feature Cards / Pills
    pills = [
        ("⚡ 1-Click Auto Downgrade", (139, 92, 246), (167, 139, 250)),
        ("🔒 Steam Update Shield", (16, 185, 129), (52, 211, 153)),
        ("💾 Safe GD Progress Backups", (56, 189, 248), (125, 211, 252)),
        ("🛡️ 100% Open Source Safe", (245, 158, 11), (251, 191, 36)),
    ]

    p_total_w = len(pills) * 260 + (len(pills) - 1) * 16
    p_start_x = width // 2 - p_total_w // 2
    p_y = height - 210

    for idx, (p_text, p_bg, p_border) in enumerate(pills):
        px = p_start_x + idx * (260 + 16)
        draw.rounded_rectangle([px, p_y, px + 260, p_y + 70], radius=14, fill=(26, 35, 51, 230), outline=p_border, width=2)
        pt_bbox = draw.textbbox((0, 0), p_text, font=pill_font)
        pt_w = pt_bbox[2] - pt_bbox[0]
        pt_h = pt_bbox[3] - pt_bbox[1]
        draw.text((px + 130 - pt_w // 2, p_y + 35 - pt_h // 2), p_text, fill=(255, 255, 255), font=pill_font)

    # Bottom Call To Action / Footer
    bottom_cta = "Download Free: github.com/willmakesrandomshit/GeodeSync"
    b_bbox = draw.textbbox((0, 0), bottom_cta, font=badge_font)
    b_w = b_bbox[2] - b_bbox[0]
    draw.text((width // 2 - b_w // 2, height - 70), bottom_cta, fill=(148, 163, 184, 255), font=badge_font)

    base.save(output_path, "PNG")
    print(f"Created: {output_path} ({width}x{height})")
    return base

if __name__ == "__main__":
    assets_dir = r"C:\Users\Owner\.gemini\antigravity\scratch\gd-version-switcher\assets"
    os.makedirs(assets_dir, exist_ok=True)
    
    # 1. 16:9 YouTube / TikTok Thumbnail (1280x720)
    thumb_path = os.path.join(assets_dir, "thumbnail.png")
    create_geodesync_thumbnail(output_path=thumb_path, width=1280, height=720)

    # 2. 2:1 GitHub Social Preview Banner (1280x640)
    banner_path = os.path.join(assets_dir, "banner.png")
    create_geodesync_thumbnail(output_path=banner_path, width=1280, height=640)

    # 3. Copy to Downloads for easy user access
    dl_dir = r"C:\Users\Owner\Downloads"
    create_geodesync_thumbnail(output_path=os.path.join(dl_dir, "GeodeSync-Thumbnail.png"), width=1280, height=720)
    create_geodesync_thumbnail(output_path=os.path.join(dl_dir, "GeodeSync-Banner.png"), width=1280, height=640)
