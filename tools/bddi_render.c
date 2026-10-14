/*
 * tools/bddi_render.c -- offline x86 renderer for the BDDI core.
 *
 * Reads a 16-bit PCM WAV (mono or stereo), processes through Bddi_process,
 * writes stereo 16-bit WAV (same signal both channels). Same code path as
 * the VST/ZDL (no python, no emulator).
 *
 * usage: bddi_render <in.wav> <out.wav> [presence drive blend bass treble
 *                     mid level mode]
 *   all params in 0..1 (mode: 0=v1l 0.5=v1e 1.0=v2) -- defaults are the
 *   factory-ish setting: 0.5 0.35 1.0 0.5 0.5 0.5 0.6 0.0
 */
#ifdef _MSC_VER
#define _CRT_SECURE_NO_WARNINGS
#endif
#include "bddi.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_SAMPLES (16u * 1024u * 1024u)

static int read_wav(const char* path, float** out, unsigned* n_out) {
    FILE* f = fopen(path, "rb");
    char hdr[12];
    unsigned rate = 0, ch = 0, bits = 0, data_len = 0;
    int found = 0;
    unsigned char* data = 0;
    if (!f) { fprintf(stderr, "cannot open %s\n", path); return -1; }
    if (fread(hdr, 1, 12, f) != 12 || memcmp(hdr, "RIFF", 4) || memcmp(hdr + 8, "WAVE", 4)) {
        fprintf(stderr, "%s: not RIFF/WAVE\n", path); fclose(f); return -1;
    }
    for (;;) {
        char ck[8]; unsigned sz;
        if (fread(ck, 1, 8, f) != 8) break;
        sz = (unsigned char)ck[4] | ((unsigned char)ck[5] << 8) |
             ((unsigned char)ck[6] << 16) | ((unsigned char)ck[7] << 24);
        if (!memcmp(ck, "fmt ", 4)) {
            unsigned char fmt[16]; unsigned got = (unsigned)fread(fmt, 1, sz < 16 ? sz : 16, f);
            if (sz < 16 || got < 16) break;
            ch = fmt[2] | (fmt[3] << 8);
            rate = fmt[4] | (fmt[5] << 8) | (fmt[6] << 16) | (fmt[7] << 24);
            bits = fmt[14] | (fmt[15] << 8);
            if (sz > 16) fseek(f, sz - 16, SEEK_CUR);
        } else if (!memcmp(ck, "data", 4)) {
            data = (unsigned char*)malloc(sz);
            if (!data) { fclose(f); return -1; }
            if (fread(data, 1, sz, f) != sz) { free(data); fclose(f); return -1; }
            data_len = sz; found = 1; break;
        } else {
            fseek(f, sz + (sz & 1), SEEK_CUR);
        }
    }
    fclose(f);
    if (!found || bits != 16 || (ch != 1 && ch != 2) || !rate) {
        fprintf(stderr, "%s: need PCM16 mono/stereo (ch=%u bits=%u)\n", path, ch, bits);
        free(data); return -1;
    }
    {
        unsigned frames = data_len / (2u * ch);
        unsigned i;
        float* buf = (float*)malloc(frames * sizeof(float));
        if (!buf) { free(data); return -1; }
        for (i = 0; i < frames; i++) {
            float s = 0.0f;
            unsigned c;
            for (c = 0; c < ch; c++) {
                short v = (short)(data[(i * ch + c) * 2] | (data[(i * ch + c) * 2 + 1] << 8));
                s += (float)v / 32768.0f;
            }
            buf[i] = s / (float)ch;
        }
        free(data);
        *out = buf; *n_out = frames;
    }
    return (int)rate;
}

int main(int argc, char** argv) {
    float* in; unsigned n = 0; int rate; unsigned i;
    int nargs = argc - 3;
    float p[8];
    Bddi* a;
    void* mem;
    FILE* fo;
    unsigned char* outb;
    int modei;

    if (argc < 3) {
        fprintf(stderr, "usage: bddi_render in.wav out.wav [presence drive blend bass treble mid level mode]\n");
        return 2;
    }
    p[0] = 0.50f; p[1] = 0.35f; p[2] = 1.00f; p[3] = 0.50f;
    p[4] = 0.50f; p[5] = 0.50f; p[6] = 0.60f; p[7] = 0.00f;
    for (modei = 0; modei < nargs && modei < 8; modei++) p[modei] = (float)atof(argv[3 + modei]);

    rate = read_wav(argv[1], &in, &n);
    if (rate < 0) return 1;
    if (n > MAX_SAMPLES) { fprintf(stderr, "too long\n"); free(in); return 1; }

    mem = malloc(Bddi_state_size((float)rate));
    a = Bddi_init(mem, Bddi_state_size((float)rate), (float)rate);
    if (!a) { fprintf(stderr, "init failed\n"); free(in); free(mem); return 1; }
    {
        int k;
        for (k = 0; k < 8; k++) Bddi_set_param(a, (BddiParam)k, p[k]);
    }

    outb = (unsigned char*)malloc((size_t)n * 4);
    {
        unsigned nan_count = 0;
        float peak = 0.0f;
        double sumsq = 0.0;
    for (i = 0; i < n; i++) {
        float y = 0.0f;
        int s;
        Bddi_process(a, in[i], &y);
        if (!(y == y)) { nan_count++; y = 0.0f; }
        { float ay = y < 0.0f ? -y : y; if (ay > peak) peak = ay; sumsq += (double)y * y; }
        if (y > 1.0f) y = 1.0f;
        if (y < -1.0f) y = -1.0f;
        s = (int)(y * 32767.0f);
        outb[i * 4 + 0] = (unsigned char)(s & 0xFF);
        outb[i * 4 + 1] = (unsigned char)((s >> 8) & 0xFF);
        outb[i * 4 + 2] = outb[i * 4 + 0];
        outb[i * 4 + 3] = outb[i * 4 + 1];
    }
        fprintf(stderr, "stats: peak=%.4f rms=%.4f nan=%u\n",
                peak, (float)__builtin_sqrt(sumsq / (double)(n ? n : 1)), nan_count);
    }
    fo = fopen(argv[2], "wb");
    if (!fo) { fprintf(stderr, "cannot write %s\n", argv[2]); free(in); free(outb); free(mem); return 1; }
    {
        unsigned data_len = n * 4;
        unsigned char hdr[44];
        unsigned riff_len = 36 + data_len;
        memcpy(hdr, "RIFF", 4);
        hdr[4] = (unsigned char)(riff_len & 0xFF); hdr[5] = (unsigned char)((riff_len >> 8) & 0xFF);
        hdr[6] = (unsigned char)((riff_len >> 16) & 0xFF); hdr[7] = (unsigned char)((riff_len >> 24) & 0xFF);
        memcpy(hdr + 8, "WAVEfmt ", 8);
        hdr[16] = 16; hdr[17] = 0; hdr[18] = 0; hdr[19] = 0;
        hdr[20] = 1; hdr[21] = 0;                       /* PCM */
        hdr[22] = 2; hdr[23] = 0;                       /* stereo */
        { unsigned r = (unsigned)rate;
          hdr[24] = (unsigned char)(r & 0xFF); hdr[25] = (unsigned char)((r >> 8) & 0xFF);
          hdr[26] = (unsigned char)((r >> 16) & 0xFF); hdr[27] = (unsigned char)((r >> 24) & 0xFF);
          r = (unsigned)rate * 4u;
          hdr[28] = (unsigned char)(r & 0xFF); hdr[29] = (unsigned char)((r >> 8) & 0xFF);
          hdr[30] = (unsigned char)((r >> 16) & 0xFF); hdr[31] = (unsigned char)((r >> 24) & 0xFF);
        }
        hdr[32] = 4; hdr[33] = 0; hdr[34] = 16; hdr[35] = 0;
        memcpy(hdr + 36, "data", 4);
        hdr[40] = (unsigned char)(data_len & 0xFF); hdr[41] = (unsigned char)((data_len >> 8) & 0xFF);
        hdr[42] = (unsigned char)((data_len >> 16) & 0xFF); hdr[43] = (unsigned char)((data_len >> 24) & 0xFF);
        fwrite(hdr, 1, 44, fo);
        fwrite(outb, 1, data_len, fo);
    }
    fclose(fo);
    fprintf(stderr, "ok: %u frames @ %d Hz -> %s\n", n, rate, argv[2]);
    free(in); free(outb); free(mem);
    return 0;
}
