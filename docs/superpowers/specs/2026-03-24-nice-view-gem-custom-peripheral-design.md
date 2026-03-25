# Design: nice-view-gem (left) + Custom Peripheral Image (right)

**Date:** 2026-03-24
**Repo:** corne-wireless-view-zmk-config
**ZMK version:** v0.3

---

## Goal

- Left side (central): replace stock `nice_view` with `nice_view_gem` — full WPM chart, layer indicator, BT profile, and battery gauge from the upstream M165437/nice-view-gem module.
- Right side (peripheral): replace stock `nice_view` with a local `nice_view_custom` shield that shows battery + connectivity (same as nice-view-gem peripheral) plus a **custom user image** in the main display area.
- A GitHub Actions pipeline converts source images dropped in `assets/` into 1-bit LVGL C arrays and auto-triggers a firmware build — no PAT required.
- The image slot is designed to support multiple cycling images in the future with a single code change.

---

## Architecture

### Shield split

| Side | Shield | Source |
|---|---|---|
| Left (central) | `nice_view_gem` | Upstream module — M165437/nice-view-gem @ v0.3.0 |
| Right (peripheral) | `nice_view_custom` | Local — `boards/shields/nice_view_custom/` |

Both sides use `nice_view_adapter` as the hardware adapter shield.

### Why two shields

Using the upstream `nice_view_gem` module for the left side means the WPM chart, BT symbols, and layer widget automatically receive upstream improvements when the revision is bumped in `west.yml`. The local `nice_view_custom` shield isolates all custom image code — only `widgets/art.c` ever changes, and only via the GHA pipeline.

---

## Repository structure

```
config/
  west.yml                                       # add m165437/nice-view-gem @ v0.3.0
build.yaml                                       # left: nice_view_gem, right: nice_view_custom

boards/shields/nice_view_custom/
  CMakeLists.txt                                 # compile peripheral files + art.c
  Kconfig.defconfig                              # LVGL config + LV_USE_IMG
  Kconfig.shield                                 # declare SHIELD_NICE_VIEW_CUSTOM
  nice_view_custom.conf                          # CONFIG_ZMK_DISPLAY=y, CONFIG_ZMK_DISPLAY_STATUS_SCREEN_CUSTOM=y
  nice_view_custom.overlay                       # SPI/CS pin config (copied from nice-view-gem)
  nice_view_custom.zmk.yml                       # shield metadata
  custom_status_screen.c                         # routes to peripheral_status widget
  widgets/
    util.c / util.h                              # canvas helpers, rotate_canvas() — copied from GPeye
    bolt.c                                       # BT/USB connectivity icon — copied from GPeye
    peripheral_status.c / peripheral_status.h   # layout: battery strip + image area; externs art.c symbols
    art.c                                        # GHA-GENERATED — image data + anim_imgs[] array

assets/                                          # user drops source images here (PNG/JPG)
  .gitkeep                                       # keep directory tracked

converted/                                       # ephemeral — GHA working directory only, gitignored

scripts/
  niceview_lvgl_convert.py                       # image → 1-bit LVGL C array (Pillow-based)
  write_art_c.py                                 # assembles converted/*.c → art.c (no patching of other files)

.github/workflows/
  build.yml                                      # add workflow_run trigger
  update-images.yml                              # new: triggers on assets/** push
```

`converted/` must be added to `.gitignore`.

---

## Config file changes

### `config/west.yml`

```yaml
manifest:
  remotes:
    - name: zmkfirmware
      url-base: https://github.com/zmkfirmware
    - name: m165437
      url-base: https://github.com/M165437
  projects:
    - name: zmk
      remote: zmkfirmware
      revision: v0.3
      import: app/west.yml
    - name: nice-view-gem
      remote: m165437
      revision: v0.3.0
  self:
    path: config
```

### `build.yaml`

```yaml
---
include:
  - board: nice_nano_v2
    shield: corne_left nice_view_adapter nice_view_gem
    snippet: studio-rpc-usb-uart        # left only — ZMK Studio requires USB on the central side
  - board: nice_nano_v2
    shield: corne_right nice_view_adapter nice_view_custom
    # no snippet — peripheral side does not use ZMK Studio
```

---

## `nice_view_custom` shield

### File origins

| File | Origin | Action |
|---|---|---|
| `CMakeLists.txt` | GPeye/nice-view-mod | Copy, remove central `status.c` branch; no animimg deps needed for static image |
| `Kconfig.defconfig` | GPeye/nice-view-mod | Copy; `LV_USE_IMG` sufficient for static image |
| `Kconfig.shield` | GPeye/nice-view-mod | Copy verbatim |
| `nice_view_custom.conf` | GPeye/nice-view-mod | Copy verbatim |
| `nice_view_custom.overlay` | nice-view-gem | Copy (correct SPI/CS pins for nice!view hardware) |
| `nice_view_custom.zmk.yml` | GPeye/nice-view-mod | Copy verbatim |
| `custom_status_screen.c` | GPeye/nice-view-mod | Copy verbatim |
| `widgets/util.c/h` | GPeye/nice-view-mod | Copy verbatim |
| `widgets/bolt.c` | GPeye/nice-view-mod | Copy verbatim |
| `widgets/peripheral_status.c/h` | GPeye/nice-view-mod | Modify: extern-declare `anim_imgs` from art.c |
| `widgets/art.c` | GHA-generated | Placeholder initially; fully regenerated on image push |

### Ownership contract: `art.c` owns the image data and array

`art.c` is the **only file the GHA ever writes**. It defines both the image descriptors and the `anim_imgs[]` array:

```c
// art.c — fully GHA-generated, do not hand-edit

#include <lvgl.h>

#ifndef LV_ATTRIBUTE_MEM_ALIGN
#define LV_ATTRIBUTE_MEM_ALIGN
#endif

// --- image data (one block per image in assets/) ---
const LV_ATTRIBUTE_MEM_ALIGN uint8_t my_image_map[] = {
    // palette (2 entries × 4 bytes = 8 bytes)
#if CONFIG_NICE_VIEW_WIDGET_INVERTED
    0xff, 0xff, 0xff, 0xff,  // index 0 = white
    0x00, 0x00, 0x00, 0xff,  // index 1 = black
#else
    0x00, 0x00, 0x00, 0xff,  // index 0 = black
    0xff, 0xff, 0xff, 0xff,  // index 1 = white
#endif
    // packed 1-bit pixel data (MSB-first, 8px/byte) ...
};

const lv_img_dsc_t my_image = {
    .header.cf = LV_IMG_CF_INDEXED_1BIT,
    .header.always_zero = 0,
    .header.reserved = 0,
    .header.w = 140,   // post-rotation width
    .header.h = 68,    // post-rotation height (image widget area, not full display)
    .data_size = sizeof(my_image_map),
    .data = my_image_map,
};

// --- animation array (extend here for future multi-image cycling) ---
// Note: no LV_IMG_DECLARE here — the symbol is defined above in this same file.
// LV_IMG_DECLARE belongs only in consuming files (peripheral_status.c).

const lv_img_dsc_t *anim_imgs[] = {
    &my_image,
};
const int anim_imgs_len = sizeof(anim_imgs) / sizeof(anim_imgs[0]);
```

`peripheral_status.c` extern-declares these symbols — it never needs to be patched:

```c
// peripheral_status.c
extern const lv_img_dsc_t *anim_imgs[];
extern const int anim_imgs_len;
```

This means `write_art_c.py` only writes `art.c`. It never touches `peripheral_status.c`.

### Static image rendering

Initial implementation uses `lv_img` (not `lv_animimg`) since there is only one image. This avoids enabling `LV_USE_ANIMIMG` in Kconfig for now.

**Upgrade path to multi-image cycling:** When a second image is added to `assets/`, the GHA regenerates `art.c` with both image descriptors and updates `anim_imgs[]`. At that point, `peripheral_status.c` is updated once (by hand) to switch from `lv_img` to `lv_animimg` with `LV_ANIM_REPEAT_INFINITE`, and `LV_USE_ANIMIMG` + `LV_USE_ANIMATION` are added to `Kconfig.defconfig`. This is a one-time manual step.

---

## Image conversion pipeline

### Display dimensions

The nice!view display is **160px wide × 68px tall** (landscape orientation). The peripheral layout reserves the top ~20px for the battery/connectivity strip, leaving approximately **140×68px** for the image widget area.

Source images are treated as portrait (68px wide × 140px tall). The converter rotates them 90° CW to produce the landscape-oriented pixel data. The resulting LVGL image descriptor is `header.w = 140, header.h = 68`.

### Image specs
- **Input:** any common format (PNG, JPG, BMP), any resolution — converter handles resize
- **Resize target:** 68×140px (portrait, before rotation)
- **Post-rotation LVGL dimensions:** `header.w = 140`, `header.h = 68`
- **Color format:** `LV_IMG_CF_INDEXED_1BIT` — 1-bit indexed, 2-entry palette
- **Palette:** `CONFIG_NICE_VIEW_WIDGET_INVERTED`-conditional (see art.c block above)
- **Dithering:** Floyd-Steinberg by default; `--no-dither` flag available
- **Bit order:** MSB-first (bit 7 = leftmost pixel)
- **Variable name:** derived from filename stem — keep filenames alphanumeric + underscores

### `niceview_lvgl_convert.py`
- Resizes input to 68×140, rotates 90° CW, dithers to 1-bit, packs to bytes (MSB-first)
- Emits a `.c` file in `converted/` with the `LV_IMG_CF_INDEXED_1BIT` descriptor and palette block
- One output file per input image

### `write_art_c.py`
- Reads all `.c` files from `converted/`
- Assembles `boards/shields/nice_view_custom/widgets/art.c`:
  - Shared LVGL header (`#include <lvgl.h>`, `LV_ATTRIBUTE_MEM_ALIGN` guard)
  - All image data blocks (one per converted file)
  - `anim_imgs[]` array
  - `anim_imgs_len` constant
  - No `LV_IMG_DECLARE` lines — symbols are defined in this file; `peripheral_status.c` uses `extern` directly
- Does **not** modify any other file

---

## GitHub Actions workflows

### `update-images.yml` (new)

```yaml
name: Update Nice!View Images
on:
  push:
    paths:
      - 'assets/**'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  update-images:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install Pillow
      - name: Convert images
        run: |
          mkdir -p converted
          find assets -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" \) \
            -exec python3 scripts/niceview_lvgl_convert.py {} --outdir converted \;
      - name: Write art.c
        run: python3 scripts/write_art_c.py
      - name: Commit and push
        run: |
          git config user.email "action@github.com"
          git config user.name "GitHub Action"
          git add boards/shields/nice_view_custom/widgets/art.c
          git diff --staged --quiet || git commit -m "chore: regenerate nice!view art from assets"
          git push
```

Uses `GITHUB_TOKEN` — no PAT required. The commit pushed here will **not** re-trigger `build.yml` via `push` (GitHub's loop protection). The `workflow_run` trigger in `build.yml` handles this instead.

### `build.yml` (modified)

```yaml
on:
  push:
  pull_request:
  workflow_dispatch:
  workflow_run:
    workflows: ["Update Nice!View Images"]
    types: [completed]

jobs:
  build:
    uses: zmkfirmware/zmk/.github/workflows/build-user-config.yml@v0.3
```

### Trigger flows

**Keymap change:**
```
push corne.keymap → build.yml fires (push trigger) → firmware artifact
```

**Image update:**
```
push to assets/ → update-images.yml fires → converts + commits art.c (GITHUB_TOKEN)
               → update-images.yml completes → workflow_run triggers build.yml → firmware artifact
```

### Deployment note

`workflow_run` only fires when the **triggering workflow is on the default branch**. During initial setup — when adding `update-images.yml` and the modified `build.yml` for the first time — both files must be merged to `master` before the automatic `workflow_run` chain is active. On the first merge commit, trigger the build manually once via `workflow_dispatch` to verify the full chain.

---

## Design decisions & rationale

| Decision | Rationale |
|---|---|
| Upstream `nice_view_gem` for left | Automatic upstream improvements; zero local maintenance |
| Local `nice_view_custom` for right | Isolates custom image code; only `art.c` ever changes |
| Based on GPeye/nice-view-mod pattern | Well-established community approach (27⭐, tutorial repo) |
| `art.c` owns `anim_imgs[]` array | GHA only writes one file; no patching of hand-authored files |
| `extern` declarations in `peripheral_status.c` | Decouples display logic from image data entirely |
| `lv_img` for initial single-image case | Avoids `LV_USE_ANIMIMG` Kconfig complexity until needed |
| `GITHUB_TOKEN` + `workflow_run` | No PAT needed; bypasses push-loop restriction cleanly |
| Python/Pillow for conversion | Scriptable in GHA; matches LVGL online converter output |
| Floyd-Steinberg dither on by default | Significantly better 1-bit rendering vs. hard threshold |
| `converted/` is ephemeral (gitignored) | Intermediate artifacts don't pollute the repo |

---

## Out of scope

- Modifying the left side display layout (nice-view-gem defaults used as-is)
- Reactive/animated images responding to WPM or keystrokes (peripheral has no input access in ZMK)
- Color or grayscale images (nice!view is 1-bit only)
- Multi-image cycling (deferred; upgrade path documented above)
