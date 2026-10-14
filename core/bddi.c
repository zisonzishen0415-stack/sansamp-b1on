/*
 * bddi.c -- SansAmp Bass Driver DI (V1 late, 2004+) white-box-style model.
 *
 * Structure is taken stage-by-stage from the traced schematic
 * (references/09_284_05_*_v1l_schematic.png, docs/CIRCUIT_V1_LATE.md):
 *
 *   input buffer -> PRESENCE shaper (IC2A) + fixed 430 Hz notch
 *   -> DRIVE gain stage (module IC10A/B) with anti-series 3.3 V zener pair
 *      solved per sample via diode-equation Newton iteration
 *      + zener junction-capacitance HF loss (drive dependent, LP)
 *   -> cabinet-simulation filter network (IC2C/IC2D)  [fitted v0]
 *   -> BLEND (dry/wet) -> LEVEL -> tone network (BASS/TREBLE peaking; V2 MID)
 *   -> MMBFJ202 JFET stages (soft saturation) -> output HPF
 *
 * Status of each stage (exact-derived vs fitted) is tracked in
 * docs/CIRCUIT_V1_LATE.md. v0 numbers are component-informed and tuned by
 * the x86 renderer; the ZDL path uses the same core unchanged.
 *
 * ZDL-safe: no allocation, no libm at runtime (Newton uses +,-,*,/
 * only; expf replaced by a polynomial), no switch statements.
 */
#include "bddi.h"

#ifdef BDDI_ZDL_STATIC
#define BDDI_API static
#define BDDI_FLUSH_DENORM(x) \
    do { float _v = (x); if (_v > -1e-30f && _v < 1e-30f) _v = 0.0f; (x) = _v; } while (0)
#else
#define BDDI_API
#define BDDI_FLUSH_DENORM(x) do { } while (0)
#endif

typedef struct {
    float b0, b1, b2, a1, a2;
    float v1, v2;
} Bq;

typedef struct {
    float sample_rate;

    /* params (normalized 0..1) */
    float presence, drive, blend, bass, treble, mid, level;
    int   mode;                 /* 0=V1L 1=V1E 2=V2 */

    /* derived gains */
    float drive_g;              /* DRIVE stage gain */
    float zener_v;              /* effective clip voltage (volts domain) */
    float level_g;

    /* state */
    float z_lp_x;               /* zener junction-cap LP state */
    Bq notch;                   /* 430 Hz fixed mid cut (V1E/V1L) */
    Bq pres;                    /* presence shelf */
    Bq cab_dip;                 /* cab mid character (fitted) */
    Bq cab_lp;                  /* cab top roll-off */
    Bq bass_p;                  /* tone: bass peaking */
    Bq treb_p;                  /* tone: treble peaking */
    Bq mid_p;                   /* tone: V2 mid peaking */
    Bq tr_roll;                 /* treble-pot pin-1 cap: HF roll track */
    float out_hp_x, out_hp_y;   /* output/INST HPF (1st order) */
    float j1, j2;               /* JFET stage dc-ish states (unused v0) */

    BddiParam last_p;           /* bookkeeping for if-else dispatch */
} BddiState;

struct Bddi { BddiState s; };

/* forward decl: with BDDI_ZDL_STATIC the header hides the extern
 * prototypes, and Bddi_init calls Bddi_reset before its definition
 * (an implicit declaration here once produced an unresolved external
 * that the obj safety audit correctly rejected). */
BDDI_API void Bddi_reset(Bddi* a);

/* ------------------------------------------------------------------ */
/* small math helpers (libm-free for the ZDL build)                    */
/* ------------------------------------------------------------------ */

/* exp(x) for x <= 0-ish small range, polynomial (Hart). Used only inside
 * the zener Newton solve where |x| < ~8. */
static float bddi_exp(float x) {
    /* 5th-order minimax on [-8,0]: e^x = 1/(1 + ...) form is unstable;
     * use exp(x)= (2^k)*exp(r) split: k = floor(x/ln2), r in [0,ln2). */
    float k = 0.0f;
    while (x < 0.0f) { x += 0.6931472f; k += 1.0f; }
    while (x >= 0.6931472f) { x -= 0.6931472f; k -= 1.0f; }
    /* e^r, r in [0, ln2): 5th order Taylor is plenty */
    float r = 1.0f + x * (1.0f + x * (0.5f + x * (0.16666667f + x * (0.041666667f + x * 0.008333333f))));
    while (k > 0.0f)  { r *= 0.5f;  k -= 1.0f; }
    while (k < 0.0f)  { r *= 2.0f;  k += 1.0f; }
    return r;
}

static float bddi_clamp01(float x) {
    if (x < 0.0f) return 0.0f;
    if (x > 1.0f) return 1.0f;
    return x;
}

/* ------------------------------------------------------------------ */
/* biquad primitives (same transposed DF2 as ampneve)                  */
/* ------------------------------------------------------------------ */

static void bq_set(Bq* b, float b0, float b1, float b2, float a1, float a2) {
    b->b0 = b0; b->b1 = b1; b->b2 = b2; b->a1 = a1; b->a2 = a2;
}

/*
 * RBJ cookbook filters, coefficients normalized to a0=1.
 * (Polynomial-only; the one division per coefficient set happens at
 *  set_param time, not per sample.)
 */
static void bq_peaking(Bq* b, float sr, float f, float q, float db) {
    /* A = 10^(db/40): approximate with 2^(db/13.3) since 10^0.025 = 2^0.083 */
    float A  = 1.0f + db * 0.057565f + db * db * 0.0016576f;  /* fit of 10^(db/40) on [-24,24] */
    float w  = 6.2831853f * f / sr;
    float cw = 1.0f, sw;
    /* sin/cos via series around w (f << sr/2 in all our uses) */
    sw = w * (1.0f - w * w * (0.16666667f - w * w * 0.008333333f));
    cw = 1.0f - w * w * (0.5f - w * w * (0.041666667f - w * w * 0.0013888889f));
    float alpha = sw / (2.0f * q);
    float a0 = 1.0f + alpha / A;
    bq_set(b,
        (1.0f + alpha * A) / a0,
        (-2.0f * cw) / a0,
        (1.0f - alpha * A) / a0,
        (-2.0f * cw) / a0,
        (1.0f - alpha / A) / a0);
}

static void bq_notch(Bq* b, float sr, float f, float q) {
    float w  = 6.2831853f * f / sr;
    float sw = w * (1.0f - w * w * (0.16666667f - w * w * 0.008333333f));
    float cw = 1.0f - w * w * (0.5f - w * w * (0.041666667f - w * w * 0.0013888889f));
    float alpha = sw / (2.0f * q);
    float a0 = 1.0f + alpha;
    bq_set(b, 1.0f / a0, (-2.0f * cw) / a0, 1.0f / a0,
              (-2.0f * cw) / a0, (1.0f - alpha) / a0);
}

static void bq_lowpass(Bq* b, float sr, float f, float q) {
    float w  = 6.2831853f * f / sr;
    float sw = w * (1.0f - w * w * (0.16666667f - w * w * 0.008333333f));
    float cw = 1.0f - w * w * (0.5f - w * w * (0.041666667f - w * w * 0.0013888889f));
    float alpha = sw / (2.0f * q);
    float a0 = 1.0f + alpha;
    bq_set(b,
        ((1.0f - cw) * 0.5f) / a0,
        (1.0f - cw) / a0,
        ((1.0f - cw) * 0.5f) / a0,
        (-2.0f * cw) / a0,
        (1.0f - alpha) / a0);
}

static float bddi_sqrt(float x) {
    float g;
    int i;
    if (x <= 0.0f) return 0.0f;
    g = x > 1.0f ? x : 1.0f;
    for (i = 0; i < 12; i++) g = 0.5f * (g + x / g);
    return g;
}

static void bq_highshelf(Bq* b, float sr, float f, float db) {
    float A  = 1.0f + db * 0.057565f + db * db * 0.0016576f;
    float w  = 6.2831853f * f / sr;
    float sw = w * (1.0f - w * w * (0.16666667f - w * w * 0.008333333f));
    float cw = 1.0f - w * w * (0.5f - w * w * (0.041666667f - w * w * 0.0013888889f));
    float alpha = sw * 0.70710678f;          /* S=1 -> alpha = sin(w)/2*sqrt(2) */
    float beta  = 2.0f * bddi_sqrt(A) * alpha;
    float a0 = (A + 1.0f) - (A - 1.0f) * cw + beta;
    bq_set(b,
        (A * ((A + 1.0f) + (A - 1.0f) * cw + beta)) / a0,
        (-2.0f * A * ((A - 1.0f) + (A + 1.0f) * cw)) / a0,
        (A * ((A + 1.0f) + (A - 1.0f) * cw - beta)) / a0,
        (2.0f * ((A - 1.0f) - (A + 1.0f) * cw)) / a0,
        ((A + 1.0f) - (A - 1.0f) * cw - beta) / a0);
}

static float bq_run(Bq* b, float x) {
    float v = x - b->a1 * b->v1 - b->a2 * b->v2;
    float y = b->b0 * v + b->b1 * b->v1 + b->b2 * b->v2;
    b->v2 = b->v1;
    b->v1 = v;
    BDDI_FLUSH_DENORM(b->v1);
    BDDI_FLUSH_DENORM(b->v2);
    return y;
}

/* ------------------------------------------------------------------ */
/* zener clipper:  anti-series 3.3 V zener pair (D100/D101 DZ2C3V3)    */
/* plus the module's series resistance, solved by Newton on            */
/*   f(v) = (v - vin)/Rs + 2*Is*sinh-ish forward/backward zener law    */
/* v0 uses the ideal-knee law: I(v) = 0 for |v|<Vz, else (|v|-Vz)/Rz . */
/* Smooth knee via exponential: I = Is*(e^{(v-Vz)/Vt} - e^{-(v+Vz)/Vt}) */
/* ------------------------------------------------------------------ */
#define ZEN_VZ   3.3f       /* zener breakdown voltage (DZ2C3V3) */
#define ZEN_VT   0.10f      /* knee softness (thermal-ish, tuned) */
#define ZEN_RS   470.0f     /* effective series R of the module path */
#define ZEN_SCALE 1.25f     /* signal->volts fullscale calibration (tuned) */

static float zener_pair(float vin) {
    /* Linear-region shortcut: for |vin| well below the knee the diode
     * current is negligible -> v = vin. This is the common case and skips
     * the Newton solve entirely (also bounds the exp loops; the full solve
     * on the real DSP at every sample cost ~110k cycles/block, measured). */
    if (vin < ZEN_VZ * 0.9f && vin > -ZEN_VZ * 0.9f) return vin;
    {
        float v = vin;
        int i;
        if (v >  ZEN_VZ + 0.5f) v =  ZEN_VZ + 0.5f;
        if (v < -ZEN_VZ - 0.5f) v = -ZEN_VZ - 0.5f;
        for (i = 0; i < 3; i++) {
            float xp = (v - ZEN_VZ) / ZEN_VT;
            float xn = (-v - ZEN_VZ) / ZEN_VT;
            float ep, en, f, df;
            if (xp > 20.0f) xp = 20.0f;
            if (xn > 20.0f) xn = 20.0f;
            ep = bddi_exp(xp);
            en = bddi_exp(xn);
            f  = (v - vin) / ZEN_RS + (ep - en) * 1e-3f;
            df = 1.0f / ZEN_RS + (ep + en) * 1e-3f / ZEN_VT;
            v -= f / df;
            if (v > 20.0f)  v = 20.0f;
            if (v < -20.0f) v = -20.0f;
            if (!(v == v)) v = 0.0f;         /* last-resort guard */
        }
        return v;
    }
}

/* ------------------------------------------------------------------ */
/* public API                                                          */
/* ------------------------------------------------------------------ */

BDDI_API uint32_t Bddi_state_size(float sample_rate) {
    (void)sample_rate;
    return (uint32_t)sizeof(struct Bddi);
}

static void update_params(BddiState* s);

BDDI_API Bddi* Bddi_init(void* mem, uint32_t bytes, float sample_rate) {
    Bddi* a;
    if (!mem || bytes < sizeof(struct Bddi)) return 0;
    if (sample_rate < 8000.0f) sample_rate = 44100.0f;
    a = (Bddi*)mem;
    a->s.sample_rate = sample_rate;
    a->s.presence = 0.5f;
    a->s.drive    = 0.35f;
    a->s.blend    = 1.00f;
    a->s.bass     = 0.5f;
    a->s.treble   = 0.5f;
    a->s.mid      = 0.5f;
    a->s.level    = 0.6f;
    a->s.mode     = 0;
    update_params(&a->s);
    Bddi_reset(a);
    return a;
}

BDDI_API void Bddi_reset(Bddi* a) {
    BddiState* s = &a->s;
    s->z_lp_x = 0.0f;
    s->notch.v1 = s->notch.v2 = 0.0f;
    s->pres.v1 = s->pres.v2 = 0.0f;
    s->cab_dip.v1 = s->cab_dip.v2 = 0.0f;
    s->cab_lp.v1 = s->cab_lp.v2 = 0.0f;
    s->bass_p.v1 = s->bass_p.v2 = 0.0f;
    s->treb_p.v1 = s->treb_p.v2 = 0.0f;
    s->mid_p.v1 = s->mid_p.v2 = 0.0f;
    s->tr_roll.v1 = s->tr_roll.v2 = 0.0f;
    s->out_hp_x = s->out_hp_y = 0.0f;
    s->j1 = s->j2 = 0.0f;
}

static void update_params(BddiState* s) {
    float sr = s->sample_rate;

    /* DRIVE pot B100k feeds the IC10B gain: clean at bottom, hard-clip on
     * top. G = 1..~31x (component-informed; refined vs renderer). */
    s->drive_g = 1.0f + s->drive * 30.0f;

    /* PRESENCE: high shelf, ~3 kHz hinge; -4..+10 dB. V1L range sits
     * higher than V1 early (per the kanengomibako analysis). */
    bq_highshelf(&s->pres, sr, 3000.0f, -4.0f + 14.0f * s->presence);

    /* Fixed ~430 Hz mid cut (V1E + V1L); absent in V2. */
    bq_notch(&s->notch, sr, 430.0f, 1.4f);

    /* Cabinet simulation (fitted v0, component-informed):
     *  - low shelf rise below ~90 Hz  (C0 group)
     *  - characteristic dip ~500 Hz
     *  - top roll-off ~4.5 kHz (speaker) */
    bq_peaking(&s->cab_dip, sr, 500.0f, 1.1f, -4.0f);
    bq_lowpass(&s->cab_lp, sr, 4500.0f, 0.8f);

    /* Tone network (V1L: peaking; V1E: shelving -> approx same v0).
     * flat at 0.5. BASS ~80 Hz, TREBLE ~3 kHz, +/- 12 dB. */
    bq_peaking(&s->bass_p, sr, (s->mode == 2) ? 60.0f : 80.0f, 0.8f,
               (s->bass - 0.5f) * 24.0f);
    bq_peaking(&s->treb_p, sr, 3000.0f, 0.8f, (s->treble - 0.5f) * 24.0f);
    /* TREBLE pot pin-1 cap: as treble comes down the very top rolls. */
    bq_lowpass(&s->tr_roll, sr, 12000.0f, 0.7f);

    /* V2 only: MID peaking ~500 Hz (shift range 400-900). */
    bq_peaking(&s->mid_p, sr, 500.0f, 0.9f, (s->mode == 2) ? (s->mid - 0.5f) * 24.0f : 0.0f);

    /* LEVEL pot + output gain. */
    s->level_g = 0.2f + 1.3f * s->level;

    /* zener junction capacitance: HF loss grows with drive (the V2 note
     * about zener terminal capacitance; fitted 30k->8k). */
    s->zener_v = (ZEN_VZ + 0.7f) * ZEN_SCALE;   /* clamp in signal domain */
}

BDDI_API void Bddi_set_param(Bddi* a, BddiParam p, float v) {
    BddiState* s = &a->s;
    v = bddi_clamp01(v);
    if (p == BDDI_PARAM_PRESENCE)     s->presence = v;
    else if (p == BDDI_PARAM_DRIVE)   s->drive = v;
    else if (p == BDDI_PARAM_BLEND)   s->blend = v;
    else if (p == BDDI_PARAM_BASS)    s->bass = v;
    else if (p == BDDI_PARAM_TREBLE)  s->treble = v;
    else if (p == BDDI_PARAM_MID)     s->mid = v;
    else if (p == BDDI_PARAM_LEVEL)   s->level = v;
    else if (p == BDDI_PARAM_MODE)    s->mode = (int)(v * 2.5f); /* 0/1/2 */
    update_params(s);
}

BDDI_API float Bddi_get_param(const Bddi* a, BddiParam p) {
    const BddiState* s = &a->s;
    if (p == BDDI_PARAM_PRESENCE)     return s->presence;
    else if (p == BDDI_PARAM_DRIVE)   return s->drive;
    else if (p == BDDI_PARAM_BLEND)   return s->blend;
    else if (p == BDDI_PARAM_BASS)    return s->bass;
    else if (p == BDDI_PARAM_TREBLE)  return s->treble;
    else if (p == BDDI_PARAM_MID)     return s->mid;
    else if (p == BDDI_PARAM_LEVEL)   return s->level;
    else if (p == BDDI_PARAM_MODE)    return (float)s->mode / 2.0f;
    return 0.0f;
}

BDDI_API void Bddi_process(Bddi* a, float in, float* out) {
    BddiState* s = &a->s;
    float dry = in;
    float x = in;

    /* -- IC2A PRESENCE shaper + fixed 430 Hz notch -- */
    x = bq_run(&s->pres, x);
    if (s->mode != 2) x = bq_run(&s->notch, x);

    /* -- module: DRIVE gain into the anti-series zener pair, in volts.
     *    The clipped voltage itself is what flows on (the blend pot and
     *    later stages see ~Vz volts); the LEVEL pot and the JFET stages
     *    bring it back to line level. (v0 had an unphysical /gain here,
     *    which made higher DRIVE *quieter*.) -- */
    {
        float g  = s->drive_g;
        float vd = x * ZEN_SCALE * g;
        float vc = zener_pair(vd);
        x = vc / ZEN_SCALE;
        /* zener junction cap LP: fc 30k -> 8k with drive (one-pole) */
        {
            float fc = 30000.0f - 22000.0f * s->drive;
            float c  = fc / s->sample_rate;         /* one-pole coeff approx */
            if (c > 0.9f) c = 0.9f;
            s->z_lp_x += (x - s->z_lp_x) * c;
            BDDI_FLUSH_DENORM(s->z_lp_x);
            x = s->z_lp_x;
        }
    }

    /* -- cabinet simulation -- */
    x = bq_run(&s->cab_dip, x);
    x = bq_run(&s->cab_lp, x);

    /* -- BLEND (dry tap taken before the drive stage) -- */
    x = dry * (1.0f - s->blend) + x * s->blend;

    /* -- LEVEL -- */
    x *= s->level_g;

    /* -- tone: BASS / TREBLE peaking (+ MID in V2) -- */
    x = bq_run(&s->bass_p, x);
    if (s->treble < 0.49f) x = bq_run(&s->tr_roll, x);
    x = bq_run(&s->treb_p, x);
    if (s->mode == 2) x = bq_run(&s->mid_p, x);

    /* -- MMBFJ202 JFET stages: soft saturation (they ARE the output
     *    limiters of the real pedal) + a touch of 2nd harmonic -- */
    {
        float ax = x < 0.0f ? -x : x;
        x = x / (1.0f + 1.1f * ax);          /* ~tanh(1.1x)/1.1, JFET-ish */
        x += 0.04f * (x * x * (x > 0.0f ? 1.0f : -1.0f));   /* even-ish bloom */
    }

    /* -- output / INST HPF (~40 Hz) -- */
    {
        float k = 6.2831853f * 40.0f / s->sample_rate;
        if (k > 0.9f) k = 0.9f;
        s->out_hp_y = x - s->out_hp_x + s->out_hp_y * (1.0f - k);
        s->out_hp_x = x;
        BDDI_FLUSH_DENORM(s->out_hp_y);
        x = s->out_hp_y;
    }

    *out = x;
}
