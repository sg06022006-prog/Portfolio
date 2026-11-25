"""Make small browser previews. Full-size renders stay unchanged."""
from pathlib import Path
from PIL import Image

root = Path('public/images/projects')
for slug, filename in [('cafe', 'cafe.png'), ('full-scene', 'full-scene.png'), ('forest', 'forest.jpg'), ('island', 'island.jpg'), ('night-room', 'night room.png')]:
    for size in [800, 1600]:
        with Image.open(root / filename) as image:
            image.thumbnail((size, size), Image.Resampling.LANCZOS)
            image.convert('RGB').save(root / f'{slug}-{size}.webp', quality=87, method=6)
            print(slug, size, image.size)
