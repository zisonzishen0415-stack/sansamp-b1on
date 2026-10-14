/*
 * bddi.h -- SansAmp Bass Driver DI (V1 late) white-box-style core.
 *
 * Platform-independent C, no allocation, all memory caller-provided.
 * ZDL build compiles this into one translation unit with BDDI_ZDL_STATIC.
 *
 * API mirrors ampneve/core/ampsim.h so the same ZDL glue/renderer patterns
 * apply. See docs/CIRCUIT_V1_LATE.md for the schematic-derived stage table
 * and the exact-derived vs fitted status of each stage.
 */
#ifndef BDDI_H
#define BDDI_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define BDDI_NUM_PARAMS 8u   /* Presence Drive Blend Bass Treble Mid Level Mode */

typedef enum {
    BDDI_PARAM_PRESENCE = 0,   /* P1 K1 */
    BDDI_PARAM_DRIVE,          /* P1 K2 */
    BDDI_PARAM_BLEND,          /* P1 K3 */
    BDDI_PARAM_BASS,           /* P2 K1 */
    BDDI_PARAM_TREBLE,         /* P2 K2 */
    BDDI_PARAM_MID,            /* P2 K3 (V2 mode only) */
    BDDI_PARAM_LEVEL,          /* P3 K1 */
    BDDI_PARAM_MODE            /* P3 K2: 0=V1 late (default) 1=V1 early 2=V2 */
} BddiParam;

typedef struct Bddi Bddi;

#ifndef BDDI_ZDL_STATIC
uint32_t Bddi_state_size(float sample_rate);
Bddi*    Bddi_init(void* mem, uint32_t mem_size, float sample_rate);
void     Bddi_reset(Bddi* a);
void     Bddi_set_param(Bddi* a, BddiParam p, float v);   /* v in [0,1] */
float    Bddi_get_param(const Bddi* a, BddiParam p);
void     Bddi_process(Bddi* a, float in, float* out);     /* one sample */
#endif

#ifdef __cplusplus
}
#endif
#endif
