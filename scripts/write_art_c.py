#!/usr/bin/env python3
"""Assemble config/boards/shields/nice_view_gem/assets/art.c from converted/*.c files."""
import argparse
import re
from pathlib import Path

HEADER = """\
// art.c -- GHA-GENERATED -- do not hand-edit
#include <lvgl.h>
#ifndef LV_ATTRIBUTE_MEM_ALIGN
#define LV_ATTRIBUTE_MEM_ALIGN
#endif

"""
OUTPUT = Path("config/boards/shields/nice_view_gem/assets/art.c")


def assemble(converted_dir=Path("converted"), output=OUTPUT, prefix="anim_imgs"):
    files = sorted(Path(converted_dir).glob("*.c"))
    if not files:
        raise FileNotFoundError(f"No .c files in {converted_dir}")
    stems = []
    parts = [HEADER]
    for f in files:
        content = f.read_text()
        m = re.search(r"const lv_img_dsc_t\s+(\w+)\s*=", content)
        if not m:
            raise ValueError(f"No lv_img_dsc_t in {f}")
        stems.append(m.group(1))
        parts += [f"// --- {m.group(1)} ---\n", content, "\n"]
    parts += [
        f"const lv_img_dsc_t *{prefix}[] = {{\n",
        *[f"    &{s},\n" for s in stems],
        "};\n",
        f"const int {prefix}_len = sizeof({prefix}) / sizeof({prefix}[0]);\n",
    ]
    Path(output).write_text("".join(parts))
    print(f"Wrote {output} with {len(stems)} image(s): {', '.join(stems)}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--converted", default="converted")
    p.add_argument("--output", default=str(OUTPUT))
    p.add_argument("--prefix", default="anim_imgs")
    a = p.parse_args()
    assemble(a.converted, a.output, a.prefix)
