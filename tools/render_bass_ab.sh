#!/bin/bash
# Render the bass audition through the BassDriver ZDL (default + dirty). ASCII.
set -u
Z=/root/ziddle/ziddle-source-1787802520/target/release/zdlrun
S=/mnt/d/zisonzishen/development/g1oncontrol/sansamp-b1on
cd /mnt/d/zisonzishen/development/g1oncontrol/b1on-firmware-reverse
$Z $S/dist/BassDriver.ZDL $S/out/bass_audition.f32 $S/out/bass_wet_default.f32 \
   --out-wet --knobs 50,35,100,50,50,50,60,0 --budget 100000000 2>&1 | tail -1
$Z $S/dist/BassDriver.ZDL $S/out/bass_audition.f32 $S/out/bass_wet_dirty.f32 \
   --out-wet --knobs 60,80,100,55,50,50,60,0 --budget 100000000 2>&1 | tail -1
echo BASS_AB_DONE
