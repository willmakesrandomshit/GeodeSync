import os
from generate_thumbnails import create_geodesync_thumbnail

bg_file = r"C:\Users\Owner\.gemini\antigravity\brain\3c01f71c-76b7-472e-b92b-9bac3fabb33b\geodesync_banner_bg_1792704576673.jpg"
assets_dir = r"C:\Users\Owner\.gemini\antigravity\scratch\gd-version-switcher\assets"
os.makedirs(assets_dir, exist_ok=True)

# 1. 16:9 YouTube / TikTok Thumbnail (1280x720)
thumb_path = os.path.join(assets_dir, "thumbnail.png")
create_geodesync_thumbnail(bg_image_path=bg_file, output_path=thumb_path, width=1280, height=720)

# 2. 2:1 GitHub Social Preview Banner (1280x640)
banner_path = os.path.join(assets_dir, "banner.png")
create_geodesync_thumbnail(bg_image_path=bg_file, output_path=banner_path, width=1280, height=640)

# 3. Copy to Downloads for user
dl_dir = r"C:\Users\Owner\Downloads"
create_geodesync_thumbnail(bg_image_path=bg_file, output_path=os.path.join(dl_dir, "GeodeSync-Thumbnail.png"), width=1280, height=720)
create_geodesync_thumbnail(bg_image_path=bg_file, output_path=os.path.join(dl_dir, "GeodeSync-Banner.png"), width=1280, height=640)

print("All thumbnails rendered with AI background successfully!")
