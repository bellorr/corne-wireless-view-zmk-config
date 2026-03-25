#!/usr/bin/env python3
"""Convert an image to a 1-bit LVGL C array for the nice!view display.

Output: a .c file in --outdir with LV_IMG_CF_INDEXED_1BIT descriptor.
Resize to 68x140 (portrait), rotate 90 CW -> header.w=140, header.h=68.
"""
import argparse
from pathlib import Path
from PIL import Image


def parse_args(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("inputs", nargs="+")
    p.add_argument("--outdir", default="converted")
    p.add_argument("--width", type=int, default=68)
    p.add_argument("--height", type=int, default=140)
    p.add_argument("--no-dither", action="store_true")
    p.add_argument("--no-rotate", action="store_true")
    p.add_argument("--lsb-first", action="store_true")
    return p.parse_args(argv)


def process_image(path, args):
    path = Path(path)
    stem = "".join(c if c.isalnum() else "_" for c in path.stem)
    with Image.open(path) as im:
        im = im.convert("L").resize((args.width, args.height), Image.LANCZOS)
        if not args.no_rotate:
            im = im.transpose(Image.ROTATE_270)
        bw = im.convert("1") if not args.no_dither else im.point(lambda p: 255 if p >= 128 else 0, "1")
        w, h = bw.size
        pix = bw.load()
        out = bytearray()
        for y in range(h):
            acc, count = 0, 0
            for x in range(w):
                bit = 1 if pix[x, y] == 255 else 0
                acc = (acc << 1) | bit if not args.lsb_first else acc | (bit << count)
                count += 1
                if count == 8:
                    out.append(acc & 0xFF)
                    acc = count = 0
            if count:
                out.append((acc << (8 - count) & 0xFF) if not args.lsb_first else acc & 0xFF)

    macro = stem.upper()
    hexes = ", ".join(f"0x{b:02X}" for b in out)
    c = f"""\
#ifndef LV_ATTRIBUTE_IMG_{macro}
#define LV_ATTRIBUTE_IMG_{macro}
#endif

const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_IMG_{macro} uint8_t {stem}_map[] = {{
#if CONFIG_NICE_VIEW_WIDGET_INVERTED
    0xff, 0xff, 0xff, 0xff, /*Color of index 0*/
    0x00, 0x00, 0x00, 0xff, /*Color of index 1*/
#else
    0x00, 0x00, 0x00, 0xff, /*Color of index 0*/
    0xff, 0xff, 0xff, 0xff, /*Color of index 1*/
#endif
    {hexes}
}};

const lv_img_dsc_t {stem} = {{
    .header.cf = LV_IMG_CF_INDEXED_1BIT,
    .header.always_zero = 0,
    .header.reserved = 0,
    .header.w = {w},
    .header.h = {h},
    .data_size = sizeof({stem}_map),
    .data = {stem}_map,
}};
"""
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{stem}.c").write_text(c)
    return outdir / f"{stem}.c", len(out)


def main():
    args = parse_args()
    for inp in args.inputs:
        p = Path(inp)
        if not p.exists():
            print(f"[WARN] {p} not found")
            continue
        out, n = process_image(p, args)
        print(f"  {p.name} -> {out} ({n} bytes)")

if __name__ == "__main__":
    main()
