#!/bin/bash
# Build + run the x86 BDDI renderer on the standard audition guitar.
# Presets: default (factory-ish), clean-ish, dirty. ASCII only.
set -u
R=/mnt/d/zisonzishen/development/g1oncontrol/sansamp-b1on
G=/mnt/d/zisonzishen/development/g1oncontrol/b1on-firmware-reverse
cd "$R/tools"
gcc -O2 -Wall -I../core -o /tmp/bddi_render bddi_render.c ../core/bddi.c -lm 2>&1 | tail -8
mkdir -p "$R/out"
IN="$G/work/desc/audition_gtr.wav"
echo "== default (P .5 D .35 B 1.0 b .5 t .5 m .5 L .6 mode V1L) =="
/tmp/bddi_render "$IN" "$R/out/bddi_v0_default.wav" 0.5 0.35 1.0 0.5 0.5 0.5 0.6 0.0
echo "== clean (drive .15) =="
/tmp/bddi_render "$IN" "$R/out/bddi_v0_clean.wav"   0.5 0.15 1.0 0.5 0.5 0.5 0.6 0.0
echo "== dirty (drive .8) =="
/tmp/bddi_render "$IN" "$R/out/bddi_v0_dirty.wav"   0.6 0.80 1.0 0.5 0.5 0.5 0.6 0.0
echo "== V2 mode (mid .6) =="
/tmp/bddi_render "$IN" "$R/out/bddi_v0_v2.wav"      0.5 0.40 1.0 0.5 0.5 0.6 0.6 1.0
echo RENDER_DONE
