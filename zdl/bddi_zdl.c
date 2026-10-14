/*
 * bddi_zdl.c -- SansAmp Bass Driver DI white-box model as a Zoom ZDL.
 *
 * Single translation unit (the linker takes one .obj): BDDI_ZDL_STATIC
 * folds the core API into internal functions and enables denormal flush.
 * Persistent state is carved lazily from the host ctx[3] arena, guarded
 * by a magic header. Output is written in place into ctx[5] (the WET
 * buffer), the convention of this build lineage. Magic shuttle ctx[11]/[12]
 * is preserved on every callback.
 *
 * Knobs: P1 Presence/Drive/Blend  P2 Bass/Treble/Mid  P3 Level/Mode.
 */
#include <stdint.h>

#define BDDI_ZDL_STATIC 1
#include "../core/bddi.c"

#ifndef BDDI_DRV_AUDIO_FUNC
#define BDDI_DRV_AUDIO_FUNC Fx_AMP_BassDriver
#endif
#ifndef BDDI_DRV_INIT_FUNC
#define BDDI_DRV_INIT_FUNC Fx_AMP_BassDriver_init
#endif

#define BDDI_DO_PRAGMA(x) _Pragma(#x)
#define BDDI_EXPAND_PRAGMA(x) BDDI_DO_PRAGMA(x)
#define BDDI_CODE_SECTION(func) BDDI_EXPAND_PRAGMA(CODE_SECTION(func, ".audio"))
BDDI_CODE_SECTION(BDDI_DRV_AUDIO_FUNC)

#define ZDL_PTR(type, word) ((type)(uintptr_t)(word))

#define BDDI_MAGIC 0x42444431u    /* "BDD1" */
#define BDDI_VERSION 1u
#define BDDI_RAW_MAX 0.14f
#define BDDI_RAW_TO_NORM 7.1428571f

typedef struct BddiZdlState {
    uint32_t magic;
    uint32_t version;
    uint32_t initialized;
    uint32_t reserved;
    unsigned char core[1];      /* Bddi instance starts here (aligned by design) */
} BddiZdlState;

/* param slot mapping for the 8-knob layout (index into params[]) */
#define BDDI_P_PRESENCE 5u
#define BDDI_P_DRIVE    6u
#define BDDI_P_BLEND    7u
#define BDDI_P_BASS     8u
#define BDDI_P_TREBLE   9u
#define BDDI_P_MID      10u
#define BDDI_P_LEVEL    11u
#define BDDI_P_MODE     12u

/* Normalize a host param value (0..100 raw, ~0.14 scaled rail, or 0..1). */
static inline float bddi_param_norm(float raw) {
    if (raw != raw) return 0.5f;                 /* NaN */
    if (raw < 0.0f) raw = 0.0f;
    if (raw <= (BDDI_RAW_MAX * 1.1f)) return raw * BDDI_RAW_TO_NORM;
    if (raw <= 1.0f) return raw;
    if (raw <= 100.0f) return raw * 0.01f;
    return 1.0f;
}

void BDDI_DRV_AUDIO_FUNC(unsigned int *ctx)
{
    float *params = ZDL_PTR(float *, ctx[1]);
    float *fxBuf  = ZDL_PTR(float *, ctx[5]);

    /* stock magic shuttle: preserve it first, always */
    unsigned int *magicSrc = ZDL_PTR(unsigned int *, ctx[12]);
    unsigned int *magicDst = ZDL_PTR(unsigned int *, *(unsigned int *)ZDL_PTR(unsigned int *, ctx[11]));
    *magicDst = *magicSrc;

    if (params[0] < 0.5f) return;   /* bypass: dry passthrough */

    {
        volatile unsigned int *desc = ZDL_PTR(volatile unsigned int *, ctx[3]);
        uintptr_t base, end, hdr, coreBase, requiredEnd;
        unsigned int span, need;
        BddiZdlState *st;

        if (!desc) return;
        base = (uintptr_t)desc[0];
        end  = (uintptr_t)desc[1];
        span = desc[2];
        if (base == 0u || end <= base) return;
        if ((base & 3u) != 0u || (end & 3u) != 0u || (span & 3u) != 0u) return;
        if (end - base < 4096u || span < end - base) return;

        hdr = (base + 3u) & ~(uintptr_t)3u;
        coreBase = (hdr + 16u + 3u) & ~(uintptr_t)3u;
        need = Bddi_state_size(44100.0f);
        requiredEnd = coreBase + (uintptr_t)need;
        if (requiredEnd > end) return;

        st = (BddiZdlState *)hdr;
        if (st->magic != BDDI_MAGIC || st->version != BDDI_VERSION || !st->initialized) {
            Bddi *r = Bddi_init((void *)coreBase, need, 44100.0f);
            if (!r) return;
            {
                int k;
                for (k = 0; k < 8; k++) Bddi_set_param(r, (BddiParam)k, 0.5f);
                Bddi_set_param(r, BDDI_PARAM_DRIVE, 0.35f);
                Bddi_set_param(r, BDDI_PARAM_BLEND, 1.0f);
                Bddi_set_param(r, BDDI_PARAM_LEVEL, 0.6f);
            }
            st->magic = BDDI_MAGIC;
            st->version = BDDI_VERSION;
            st->initialized = 1u;
            st->reserved = 0u;
        }

        {
            Bddi *core = (Bddi *)coreBase;
            Bddi_set_param(core, BDDI_PARAM_PRESENCE, bddi_param_norm(params[BDDI_P_PRESENCE]));
            Bddi_set_param(core, BDDI_PARAM_DRIVE,    bddi_param_norm(params[BDDI_P_DRIVE]));
            Bddi_set_param(core, BDDI_PARAM_BLEND,    bddi_param_norm(params[BDDI_P_BLEND]));
            Bddi_set_param(core, BDDI_PARAM_BASS,     bddi_param_norm(params[BDDI_P_BASS]));
            Bddi_set_param(core, BDDI_PARAM_TREBLE,   bddi_param_norm(params[BDDI_P_TREBLE]));
            Bddi_set_param(core, BDDI_PARAM_MID,      bddi_param_norm(params[BDDI_P_MID]));
            Bddi_set_param(core, BDDI_PARAM_LEVEL,    bddi_param_norm(params[BDDI_P_LEVEL]));
            Bddi_set_param(core, BDDI_PARAM_MODE,     bddi_param_norm(params[BDDI_P_MODE]));

            {
                int i;
                for (i = 0; i < 8; i++) {
                    float ol;
                    Bddi_process(core, fxBuf[i], &ol);
                    fxBuf[i] = ol;
                }
            }
        }
    }
}

/* Zoom materializes params through the _init handler (the build uses the
 * linker's materialize_init body); this object-side init is kept for the
 * fork-tree fallback path and only writes the ON flag + defaults. */
void BDDI_DRV_INIT_FUNC(unsigned int *ctx)
{
    float *params = ZDL_PTR(float *, ctx[1]);
    params[0] = 1.0f;
    params[5] = 50.0f;   /* Presence */
    params[6] = 35.0f;   /* Drive */
    params[7] = 100.0f;  /* Blend */
    params[8] = 50.0f;   /* Bass */
    params[9] = 50.0f;   /* Treble */
    params[10] = 50.0f;  /* Mid */
    params[11] = 60.0f;  /* Level */
    params[12] = 0.0f;   /* Mode: V1 late */
}
