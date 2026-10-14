#!/usr/bin/env python3
"""Build BassDriver.ZDL from zdl/bddi_zdl.c + zdl/manifest.json.

Pipeline (same as the AmpNeve/Reverson projects, see
b1on-firmware-reverse/docs/HOW_TO_MAKE_ZDL_PLUGINS.md):
  cl6x compile (single TU) -> obj safety audit (tools/check_zdl_obj.py)
  -> link with the fixed 2026-10 linker tree (materialize init via
  ZDL_MATERIALIZE_INIT=1) -> CABI block injection (gid 4 AMP).

Options:
  --smoke   link with audio_nop (pass-through); output goes to dist_smoke/.

Env: BDDI_TI_ROOT, BDDI_ZDL_ROOT, BDDI_DLL_FIELDS (3|5), BDDI_W28.
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
G1ON = ROOT.parent  # ...\g1oncontrol

ZDL_ROOT = Path(os.environ.get(
    "BDDI_ZDL_ROOT",
    str(G1ON / "zoomreverse" / "ZoomMultistompZDL-2026-10")))
if not ZDL_ROOT.exists():
    ZDL_ROOT = G1ON / "zoomreverse" / "ZoomMultistompZDL"
sys.path.insert(0, str(ZDL_ROOT / "build"))
sys.path.insert(0, str(ZDL_ROOT / "src" / "airwindows" / "common"))

from airwindows_image import make_airwindows_tape_screen  # noqa: E402
from linker import LinkerConfig, link, params_from_manifest  # noqa: E402

TI_ROOT = Path(os.environ.get(
    "BDDI_TI_ROOT",
    r"D:\ti\ti-cgt-c6000_8.3.15\ti-cgt-c6000_8.3.15"))
CL6X = TI_ROOT / "bin" / "cl6x"
if not CL6X.exists() and (TI_ROOT / "bin" / "cl6x.exe").exists():
    CL6X = TI_ROOT / "bin" / "cl6x.exe"

CFLAGS = [
    "--c99",
    "--opt_level=2",
    "-mv6740",
    "--abi=eabi",
    "--mem_model:data=far",
    f"--include_path={TI_ROOT}/include",
]


def add_cabi(zdl_path: Path, fxid: int, effect_name: str) -> None:
    """Inject the CABI block every stock G1on AMP-category ZDL carries
    (same post-link step as the AmpNeve project; floats are inert loader
    metadata -- our DSP renders no cabs, it IS the cab-sim)."""
    sys.path.insert(0, str(ZDL_ROOT / "build"))
    from zdl import HEADER_SIZE_TYPICAL, Zdl  # noqa: E402

    template = (HERE / "cabi_2x12_template.bin").read_bytes()
    if template[:4] != b"CABI":
        sys.exit("[bddi] cabi_2x12_template.bin is not a CABI block")
    cabi = bytearray(template)
    struct.pack_into("<I", cabi, 0x08, (0x04 << 24) | (fxid & 0xFFFF))
    prefix = effect_name[:2].upper().ljust(2, "\x00").encode("latin1")
    cabi[0x0C:0x0E] = prefix
    model = effect_name[:8].upper().ljust(8, "\x00").encode("latin1")
    cabi[0x14:0x1C] = model

    z = Zdl.load(zdl_path)
    z.extra_header_payload = bytes(cabi)
    z.header_size = HEADER_SIZE_TYPICAL + len(cabi)
    zdl_path.write_bytes(z.pack())
    print(f"[bddi] G1on AMP CABI block injected -> {zdl_path.name} "
          f"(header {HEADER_SIZE_TYPICAL} -> {z.header_size} bytes)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true",
                    help="audio_nop pass-through build (first flash test)")
    ap.add_argument("--no-inspect", action="store_true")
    args = ap.parse_args()

    manifest = json.loads((HERE / "manifest.json").read_text())
    name = manifest["effect_name"]

    src_c = HERE / "bddi_zdl.c"
    obj = HERE / "bddi_zdl.obj"
    out_dir = ROOT / ("dist_smoke" if args.smoke else "dist")
    out_dir.mkdir(exist_ok=True)
    out_zdl = out_dir / f"{name}.ZDL"

    print(f"[bddi] compiling {src_c.name} -> {obj.name} with {CL6X}")
    subprocess.run([str(CL6X), *CFLAGS, "-c", str(src_c),
                    f"--output_file={obj}"], check=True, cwd=HERE)

    if not args.no_inspect:
        print("[bddi] auditing", obj.name, "(tools/check_zdl_obj.py)")
        env = dict(os.environ)
        env["AMPNEVE_ZDL_ROOT"] = str(ZDL_ROOT)  # the audit reuses the same discovery
        subprocess.run([sys.executable, "-B", str(ROOT / "tools" / "check_zdl_obj.py"),
                        str(obj)], check=True, env=env)

    for junk in ("compiler.opt", "linker.cmd"):
        p = HERE / junk
        if p.exists():
            p.unlink()

    cfg = LinkerConfig(
        effect_name=name,
        audio_func_name=manifest.get("audio_func_name"),
        gid=manifest["gid"],
        fxid=manifest["fxid"],
        params=params_from_manifest(manifest["params"]),
        obj_path=obj,
        output_path=out_zdl,
        fxid_version=manifest.get("fxid_version", "1.00").encode("ascii"),
        flags_byte=manifest.get("flags_byte", 0x01),
        audio_nop=manifest.get("audio_nop", False) or args.smoke,
        screen_image=make_airwindows_tape_screen(name[:6], ""),
        # handlers: knobs 1-2 from the stock LineSel blob, 3..8 synthesized
        # clones (the pattern proven by AmpNeve; the AIR knob3 blob is not
        # used -- it hits unimplemented ops in Ziddle).
        handler_blob_path=ZDL_ROOT / "build" / "linesel_handlers.bin",
        knob3_blob_path=Path("/tmp/__nonexistent__"),
        synthesize_linesel_edit_handlers=True,
        synth_edit_start_index=2,
        use_object_edit_handlers=False,
        # amp_cabi_* only fed the lost repeat98 linker; the CABI content is
        # written post-link by add_cabi() below (lossless).
        amp_cabi_fxid=None,
        amp_cabi_default=None,
        dsp_cost=float(os.environ.get("BDDI_W28", "12.0")),
        dll_fields=int(os.environ.get("BDDI_DLL_FIELDS", "3")),
        audio_va=0,
    )
    link(cfg)

    if manifest["gid"] == 4:
        add_cabi(out_zdl, manifest["fxid"], name)

    tag = " (PASS-THROUGH - test only)" if args.smoke else ""
    print(f"\n[bddi] done -> {out_zdl}{tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
