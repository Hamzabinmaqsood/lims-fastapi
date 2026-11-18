"""Cut satellite maps to the farm shape and split them into Good / Normal / Bad maps."""

from PIL import Image, ImageChops, ImageDraw

CLASSES = {1: "good", 2: "normal", 3: "bad"}   # codes written by sentinel.class_evalscript
WHITE = (255, 255, 255)


def farm_mask(size: tuple[int, int], points: list[tuple[float, float]]) -> Image.Image:
    """White (255) inside the farm polygon, black (0) outside. points are already in pixels."""
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon(points, fill=255)
    return mask


def cut_to_farm(img: Image.Image, mask: Image.Image) -> Image.Image:
    """Keep the pixels inside the farm; everything outside becomes white."""
    white = Image.new("RGB", img.size, WHITE)
    return Image.composite(img.convert("RGB"), white, mask)


def _layer(classes: Image.Image, mask: Image.Image, code: int) -> Image.Image:
    """255 where the pixel has this class AND is inside the farm, else 0."""
    only_this = classes.point(lambda v, c=code: 255 if v == c else 0)
    return ImageChops.multiply(only_this, mask)


def class_maps(img: Image.Image, mask: Image.Image, classes: Image.Image) -> dict[str, Image.Image]:
    """One map per class that actually appears inside the farm; empty classes are skipped."""
    out = {}
    for code, name in CLASSES.items():
        keep = _layer(classes, mask, code)
        if keep.getbbox() is None:          # no pixels → no image
            continue
        out[name] = cut_to_farm(img, keep)
    return out


def class_percents(mask: Image.Image, classes: Image.Image) -> dict[str, float]:
    """% of the farm's classified (cloud-free) pixels in each class, counted from the picture itself."""
    counts = {name: _layer(classes, mask, code).histogram()[255] for code, name in CLASSES.items()}
    total = sum(counts.values())
    return {name: round(100 * n / total, 1) for name, n in counts.items()} if total else {}
