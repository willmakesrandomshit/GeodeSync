from PIL import Image, ImageDraw

def create_geode_icon(output_path):
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []

    for size in sizes:
        w, h = size
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Scale factor
        s = w / 256.0

        # Background rounded shield/cube
        margin = 12 * s
        bg_corners = [margin, margin, w - margin, h - margin]
        draw.rounded_rectangle(bg_corners, radius=36 * s, fill=(26, 32, 44, 255), outline=(139, 92, 246, 255), width=int(max(1, 6 * s)))

        # Inner crystal / cube facet 1 (Top/Left)
        p1 = (w * 0.5, 38 * s)
        p2 = (w - 38 * s, 85 * s)
        p3 = (w * 0.5, 138 * s)
        p4 = (38 * s, 85 * s)
        draw.polygon([p1, p2, p3, p4], fill=(167, 139, 250, 255), outline=(196, 181, 253, 255))

        # Facet 2 (Bottom Left)
        p5 = (38 * s, 172 * s)
        p6 = (w * 0.5, 222 * s)
        draw.polygon([p4, p3, p6, p5], fill=(139, 92, 246, 255), outline=(167, 139, 250, 255))

        # Facet 3 (Bottom Right)
        p7 = (w - 38 * s, 172 * s)
        draw.polygon([p3, p2, p7, p6], fill=(109, 40, 217, 255), outline=(139, 92, 246, 255))

        # Neon lightning / sync arrow in center
        lp = [
            (w * 0.52, 65 * s),
            (w * 0.42, 125 * s),
            (w * 0.50, 125 * s),
            (w * 0.44, 185 * s),
            (w * 0.60, 115 * s),
            (w * 0.51, 115 * s),
        ]
        draw.polygon(lp, fill=(250, 204, 21, 255))

        images.append(img)

    images[0].save(output_path, format="ICO", sizes=[(im.width, im.height) for im in images], append_images=images[1:])
    print(f"Icon created successfully at: {output_path}")

if __name__ == "__main__":
    create_geode_icon("icon.ico")
