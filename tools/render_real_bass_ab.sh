#!/bin/bash
# Render the REAL bass-DI excerpt (out/bass_real.f32) through the BassDriver
# ZDL in the Ziddle emulator (device truth) plus the native x86 core for
# reference. ASCII only.
set -u
Z=/root/ziddle/ziddle-source-1787802520/target/release/zdlrun
S=/mnt/d/zisonzishen/development/g1oncontrol/sansamp-b1on

$Z $S/dist/BassDriver.ZDL $S/out/bass_real.f32 $S/out/bass_real_wet_default.f32 \
   --out-wet --knobs 50,35,100,50,50,50,60,0 --budget 100000000 2>&1 | tail -1
$Z $S/dist/BassDriver.ZDL $S/out/bass_real.f32 $S/out/bass_real_wet_dirty.f32 \
   --out-wet --knobs 60,80,100,55,50,50,60,0 --budget 100000000 2>&1 | tail -1

cd "$S/tools"
gcc -O2 -Wall -I../core -o /tmp/bddi_render bddi_render.c ../core/bddi.c -lm 2>&1 | tail -4
/tmp/bddi_render $S/out/bass_real_dry.wav $S/out/bddi_real_x86_default.wav 0.5 0.35 1.0 0.5 0.5 0.5 0.6 0.0
/tmp/bddi_render $S/out/bass_real_dry.wav $S/out/bddi_real_x86_dirty.wav  0.6 0.80 1.0 0.55 0.5 0.5 0.6 0.0
echo REAL_BASS_WET_DONE
