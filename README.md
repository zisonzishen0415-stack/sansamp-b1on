# sansamp-b1on —— SansAmp Bass Driver DI 硬件级(白盒)复刻 → Zoom B1on ZDL

> 目标:按**电路级白盒建模**复刻 Tech 21 SansAmp Bass Driver DI,做成
> B1on/G1on 可加载的 ZDL 效果(9 旋钮三相页 + 版本模式开关)。
> **现状(2026-10-14):v0 完成** —— 核心 DSP、x86 渲染器、ZDL 构建/验证
> 全链路打通,试听已出;下一步 = 细节校音(对着参考录音/将来对着真机)。

## 交付物(v0,2026-10-14)

| 项 | 状态 |
|---|---|
| `dist/BassDriver.ZDL`(真 DSP) | `36E6D16BD2755F3AC11C47AEC88DC0E609CE6604A3ED8033D23A2E8F23B5042A` |
| `dist_smoke/BassDriver.ZDL`(烟测) | `FF88025FA614A3630124808BC7009F15389452204E385EBE6C7AC982A611A67E`(首刷用) |
| 屏幕封面(二次元像素画) | `tools/bddi_cover.py` 生成:反白 `BASS DRIVER` 标题 + Q 版双丸子头小妞 + 倚着的贝斯 + ♪/✦;预览 `out/bddi_cover_{preview_8x,device}.png`(device=模拟 1.4× 纵向拉伸 + 固件旋钮值框位置) |
| matcheck(8 参数契约) | **双 PASS**(init 物化 + handler 归一化) |
| Ziddle 模拟器全曲渲染 | 41343 块、**NaN=0**、peak 0.85/rms 0.215;中位 **~72.7k cycles/块** |
| 试听 | **`out/BassDriver_AB_default.wav`(干声 10s + 湿声 10s,贝斯)**、`out/BassDriver_AB_dirty.wav`(Drive 80 版);纯湿声旧版 `out/BassDriver_{default,dirty}_audition.wav`;干声参考 `out/bass_audition_dry.wav` |
| x86 参照渲染 | `out/bddi_v0_{default,clean,dirty,v2}.wav`(同一核心,原生编译) |

## 目标版本(待最终拍板,默认 V1 后期型)

| 版本 | 要点 | 资料 |
|---|---|---|
| V1 初期型(≤2003) | 供电压相关削波;低频/高频 shelf 型音调;有 ~430Hz 固定中频凹槽 | `references/09_283_05_*v1e*.png` |
| **V1 后期型(2004+)**(默认) | **3.3V 稳压管对削波(非对称区)**;PRESENCE 频段更高;音调改 peaking 型;2010 后个体多一颗 2.2µF 低频补偿 | `references/09_284_05_*v1l*.png` |
| V2(2016+) | CH40 模块(同构稳压管对,实测确认);**新增 MID(400-900Hz)**;去掉 430Hz 定切;高音整体略降 | 00285 页 |

B1on 侧的天然 UI 映射:**7 个旋钮**(PRESENCE/DRIVE/BLEND/BASS/TREBLE/[MID]/LEVEL)
+ 第 8 旋钮作 **Mode**(V1E / V1L / V2 三档 voicing,照 Reverson 的 Mode 写法)。

## 信号链(V1 后期型,从 traced 电路图抄录)

```
INPUT → C4(47n)/R10(10k) → 偏置 R1/R2(1M→VCOM)
→ IC2B(TLC2264) 输入缓冲
→ IC2A(TLC2264) PRESENCE 塑形网络(R26 10k / R24 3.3k / R110 10k /
   C31 10n / C32 100p / VR PRESENCE B100k)+ ~430Hz 固定中频凹槽
→ [灌封模块 CH34-x,=TLC2262 双运放 IC10A/B]
     DRIVE(VR1 B100k) 增益级 →
     IC10B 反馈环内 **DZ2C3V3 双稳压管(3.3V)对** ← 失真的核心
→ R48/R49(3.3k)/C23(47n)/C13(10µ) 耦合
→ 箱体模拟滤波网(IC2C/IC2D TLC2264:C14/C33 2.2µ/R35 100k/C34 470p/
   R36 3.3k/C30/C27 22n/C10 4.7n/R12 10k/R27 22k/C42 4.7n/C0 2.2µ*)
→ BLEND(VR6 B100k)干湿混合(干路取自输入缓冲后)
→ LEVEL(VR4 B100k) → IC3A 缓冲
→ 音调网络 IC3C(TLC2264):BASS(VR B100k)/TREBLE(VR B100k)peaking
→ T1/T2 MMBFJ202 JFET 级
→ IC3D 输出 + INST/LINE 高通开关(C43 2.2µ/C44 100n/R56 10k/R6 2.2M)
→ OUT(1/4") ;XLR 支路(IC4A/B TLC2262 + 变压器)在 ZDL 版中略去
```
\* C0 2.2µF 电解 = 2010 前后追加的低频补偿,个体差异,建模时可做开关项。

**白盒要点**:
- **非线性 = IC10B 反馈中的 3.3V 稳压管对**:逐样本解稳压管 I-V(或 Zener-多项式近似)
  + TLC2262 自身的输出削顶/摆率行为(BDI21 差异的最大来源就是换了 TL074/4558!)。
- 线性级 = 逐级 RC 网络推传递函数 → 双二阶实现(与 AmpNeve 的 Biquad 同套)。
- JFET 级 = 软饱和缓冲(MMBFJ202 特性曲线)。
- **无 IR、无卷积**——纯模拟电路 → DSP 负载远低于 AmpNeve,预算无忧。

## 开发计划

1. **阶段 1(本仓即刻)**:电路拆解 → 每级传递函数/非线性函数台账(`docs/CIRCUIT_V1_LATE.md` 持续更新)。
2. **阶段 2**:`core/bddi.c` 写成平台无关 C(仿 `ampneve/core/ampsim.c` 的 API),x86 渲染器先行试听/调音。
3. **阶段 3**:ZDL 胶水(`zdl/`,照 `ampneve/zdl/build.py` + 9 旋钮 materialize 流程)+ Mode 旋钮;
   matcheck 双 PASS + zdlrun 音频 + 与 x86 渲染对照(整套基建已就绪,见
   `b1on-firmware-reverse/docs/HOW_TO_MAKE_ZDL_PLUGINS.md`)。
4. **阶段 4**:试听对比(参考录音/BDI21)、上机清单并入主仓库 checklist。

## 资料与许可(重要)

- `references/`(traced 电路图/分析页)来自社区逆向,**原作者标注禁止商用**;
  本项目为个人非商用复刻。**references/ 不进 git**(.gitignore),只在本地留档。
- 完整来源清单(URL/每份资料提供什么/许可)见 `docs/SOURCES.md`。
- 命名:成品 ZDL 建议避开商标(如 `ZDL_AMP_BassDriver`),做法本身(独立电路
  分析+自写 DSP)无问题。

## 相关基建(复用,不重复造)

- 构建/验证全流程:`b1on-firmware-reverse/docs/HOW_TO_MAKE_ZDL_PLUGINS.md`
- 状态区/参数 ABI、materialize、reloc 修复经验:同上 + `RELOC_BUG_ROOT_CAUSE_2026-10-14.md`
- DSP 框架样板:`b1on-firmware-reverse/ampneve/`(core API / x86 渲染器 / ZDL 胶水)
