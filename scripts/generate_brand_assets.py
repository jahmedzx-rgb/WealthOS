from __future__ import annotations

import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "branding"
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def scaled(points: list[tuple[float, float]], factor: float) -> list[tuple[int, int]]:
    return [(round(x * factor), round(y * factor)) for x, y in points]


def render(size: int) -> Image.Image:
    scale = size / 256
    supersample = 4 if size <= 64 else 2
    canvas_size = size * supersample
    factor = scale * supersample
    image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def box(values: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
        return tuple(round(value * factor) for value in values)  # type: ignore[return-value]

    draw.rounded_rectangle(box((8, 8, 248, 248)), radius=round(54 * factor), fill=(8, 29, 47, 255))
    draw.rounded_rectangle(box((12, 12, 244, 244)), radius=round(50 * factor), fill=(12, 38, 62, 255))
    border=max(1,round(6*factor))
    draw.rounded_rectangle(box((17, 17, 239, 239)), radius=round(45 * factor), outline=(216, 180, 92, 195), width=border)

    w_width=max(2,round(25*factor))
    draw.line(scaled([(58,70),(91,184),(128,101),(165,184),(182,112)],factor),fill=(221,181,82,255),width=w_width,joint="curve")
    highlight=max(1,round(2*factor))
    draw.line(scaled([(62,73),(92,174),(128,92),(165,174),(185,102)],factor),fill=(240,213,143,210),width=highlight,joint="curve")
    green=(84,166,108,255)
    green_tip=[(170,109),(186,46),(181,45),(203,28),(215,53),(210,52),(194,115)]
    draw.polygon(scaled(green_tip,factor),fill=green)
    separator_width=max(supersample,round(5*factor))
    draw.line(scaled([(170,109),(194,115)],factor),fill=(12,38,62,255),width=separator_width)
    draw.line(scaled([(184,104),(195,59)],factor),fill=(145,200,159,255),width=highlight)

    return image.resize((size,size),Image.Resampling.LANCZOS)


def ico_sizes(path: Path) -> list[int]:
    data=path.read_bytes()
    _,kind,count=struct.unpack_from("<HHH",data,0)
    assert kind==1
    values=[]
    for index in range(count):
        width=data[6+index*16] or 256
        height=data[7+index*16] or 256
        assert width==height
        values.append(width)
    return values


def main() -> None:
    OUT.mkdir(parents=True,exist_ok=True)
    master=render(1024)
    master.save(OUT/"wealthos-app-icon-1024.png",optimize=True)
    for size in SIZES:
        render(size).save(OUT/f"wealthos-app-icon-{size}.png",optimize=True)
    if "--preview-only" in sys.argv:
        print(f"Generated SVG companion PNG previews in {OUT}; ICO left untouched")
        return
    master.save(OUT/"wealthos-app-icon.ico",format="ICO",sizes=[(size,size) for size in SIZES],bitmap_format="png")
    actual=ico_sizes(OUT/"wealthos-app-icon.ico")
    missing=sorted(set(SIZES)-set(actual))
    if missing:
        raise RuntimeError(f"ICO is missing sizes: {missing}; contains {actual}")
    for path in [OUT/"wealthos-app-icon-1024.png",OUT/"wealthos-app-icon.ico"]:
        with Image.open(path) as asset:
            assert asset.mode=="RGBA" or path.suffix==".ico"
    print(f"Generated SVG companion assets in {OUT}")
    print(f"ICO entries: {actual}")


if __name__=="__main__":
    main()
