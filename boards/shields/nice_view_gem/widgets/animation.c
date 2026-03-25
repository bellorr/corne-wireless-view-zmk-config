#include <stdlib.h>
#include <zephyr/kernel.h>
#include "animation.h"

// Image data defined in assets/art.c (GHA-generated).
// Add more images to assets/ and push to add cycling frames.
extern const lv_img_dsc_t *anim_imgs[];
extern const int anim_imgs_len;

void draw_animation(lv_obj_t *canvas) {
#if IS_ENABLED(CONFIG_NICE_VIEW_GEM_ANIMATION)
    lv_obj_t *art = lv_animimg_create(canvas);
    lv_obj_center(art);

    lv_animimg_set_src(art, (const void **)anim_imgs, anim_imgs_len);
    lv_animimg_set_duration(art, CONFIG_NICE_VIEW_GEM_ANIMATION_MS);
    lv_animimg_set_repeat_count(art, LV_ANIM_REPEAT_INFINITE);
    lv_animimg_start(art);
#else
    lv_obj_t *art = lv_img_create(canvas);
    lv_img_set_src(art, anim_imgs[0]);
#endif

    lv_obj_align(art, LV_ALIGN_TOP_LEFT, 36, 0);
}
