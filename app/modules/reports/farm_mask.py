"""Cut satellite maps to the farm shape and split them into Good / Normal / Bad maps."""

from PIL import Image, ImageChops, ImageDraw

from PIL import ImageFilter

MIN_SHARE = 0.01        # skip patches smaller than 1% of the farm
MAX_PER_CLASS = 6       # at most 6 patches per class
PAD = 4                 # white margin (pixels) around each cropped patch

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







def split_patches(layer: Image.Image) -> list[Image.Image]:
    """Split a 0/255 layer into separate connected patches (one 0/255 image per patch)."""
    work = layer.filter(ImageFilter.MaxFilter(3))   # grow 1 px: corner-touching blocks join
    patches = []
    for _ in range(500):                             # safety limit
        box = work.getbbox()
        if box is None:
            break
        row = work.crop((box[0], box[1], box[2], box[1] + 1)).tobytes()
        seed = (box[0] + row.index(255), box[1])     # first white pixel on the top row
        ImageDraw.floodfill(work, seed, 128)         # paint-bucket this patch grey
        grown = work.point(lambda v: 255 if v == 128 else 0)
        work = work.point(lambda v: 0 if v == 128 else v)            # remove it from the work image
        patches.append(ImageChops.multiply(grown, layer))            # back to the real pixels only
    return patches


def class_patches(img: Image.Image, mask: Image.Image, classes: Image.Image) -> dict[str, list[dict]]:
    """{"bad": [{"image": cropped map, "box": (x0, y0, x1, y1), "pct": 31.2}, ...], ...}, biggest first."""
    layers = {name: _layer(classes, mask, code) for code, name in CLASSES.items()}
    total = sum(layer.histogram()[255] for layer in layers.values())
    if not total:
        return {}
    out = {}
    for name, layer in layers.items():
        found = []
        for patch in split_patches(layer):
            n = patch.histogram()[255]
            if n < MIN_SHARE * total:
                continue                                              # too small → noise
            x0, y0, x1, y1 = patch.getbbox()
            box = (max(0, x0 - PAD), max(0, y0 - PAD), min(img.width, x1 + PAD), min(img.height, y1 + PAD))
            found.append({"image": cut_to_farm(img, patch).crop(box), "box": box, "pct": round(100 * n / total, 1)})
        found.sort(key=lambda p: p["pct"], reverse=True)
        if found:
            out[name] = found[:MAX_PER_CLASS]
    return out
