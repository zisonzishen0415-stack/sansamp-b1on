# 资料来源清单(2026-10-14 收集)

> 用途 = 白盒复刻的电路依据。**全部为社区逆向资料,非官方**;
> kanengomibako 明确标注"独立逆向、可能有误、**禁止商用**"——
> 本项目为个人非商用复刻,`references/` 本地留档、不入 git。

## 一、kanengomibako(可燃ごみ箱)——核心资料(完整 traced 电路图 + 元件值)

| 页面 | 内容 | 本地文件 |
|---|---|---|
| [00284](https://kanengomibako.github.io/pages/00284.html) | **BDDI V1 后期型**完整解析 + 全分辨率电路图(CH34-5/CH34-9 灌封模块剖开)+ 与初期型差异(稳压管削波/PRESENCE 频段/peaking 音调/C0 低频补偿电容 2010+)+ 频响仿真图 | `kanengomibako_00284.html`, `09_284_05_*v1l*_schematic.png` |
| [00283](https://kanengomibako.github.io/pages/00283.html) | BDDI **V1 初期型**解析 + 电路图 | `kanengomibako_00283.html`, `09_283_05_*v1e*_schematic.png` |
| [00285](https://kanengomibako.github.io/pages/00285.html) | BDDI **V2** 解析(CH40 模块实测=同构 3.3V 稳压管对 BZB984-C3V3;新增 MID 400-450/800-900Hz;V1 的 430Hz 定切取消;面包板克隆验证)| `kanengomibako_00285.html` |
| [00282](https://kanengomibako.github.io/pages/00282.html) | **Behringer BDI21** 完整解析 + 电路图 + 与 BDDI V1 初期型**逐元件差异表**(运放 TLC2264/2262 vs TL074/4558/4580;C4 47n→22n;C25 2.2µ→100n;C28/C32 100p→220p;C34 1n→1.2n 等) | `kanengomibako_00282.html`, `09_282_05_bdi21_schematic.png` |

## 二、其他社区分析

| 来源 | 提供什么 |
|---|---|
| [fpgacpu.ca BDI21 改造分析](https://fpgacpu.ca/analog/bdi21.html) | BDI21 的逐级电路讨论 + 修改方案(notch/HPF/presence,C26/C31/C32/R22/R25 等),可交叉校核 | `fpgacpu_bdi21_analysis.html` |
| [FSB t=422](https://www.freestompboxes.org/viewtopic.php?f=1&t=422)("Diz" 2006 traced + 项目) | 最早的 BDDI 社区 trace(Cloudflare 拦脚本抓取,浏览器可读) | 仅 URL |
| [FSB t=6571](https://www.freestompboxes.org/viewtopic.php?t=6571&start=380) | CH33-6 灌封模块首剖帖 | 仅 URL |
| [FSB t=14152](https://www.freestompboxes.org/viewtopic.php?t=14152) | BDI21≈BDDI 的确认帖:"IC2/U2 换 TLC2264 可还原 ~99% 音色"(→ 运放行为是音色关键) | 仅 URL |
| [TalkBass: SansAmp overdrive circuit](https://www.talkbass.com/threads/can-someone-explain-the-sansamp-overdrive-circuit.1614118/) | 失真位置讨论(IC3A 削顶等,注意与 V1.L 图上的编号对应关系需自行核对) | 仅 URL |

## 三、经典版(吉他)SansAmp Classic(备查,非本目标)

- 流传电路图(非官方,多处值有猜测):2SK117 仅作输入缓冲,失真在运放级;
  TL072/TL074 + 1N755 电源稳压 + 1N4148。
- [music-electronics-forum 帖](https://music-electronics-forum.com/forum/effectification/guitar-effects/42624-sansamp-classic)、
  [DIYstompboxes 102389](https://www.diystompboxes.com/smfforum/index.php?topic=102389.0)。

## 四、本项目基建参考(非电路资料)

- themanro/ZoomMultistompZDL(语料/构建链/matcheck)、Ziddle(C674x 模拟器)、
  AmpNeve(框架样板)——见 `b1on-firmware-reverse/README.md` 致谢节。

## 待补

- [ ] BDDI V1 后期型**实机干声/湿声对**(标定用;用户暂无真机 → 先用电路仿真+参考录音)
- [ ] BDI21 官方用户手册(层 2 校核,已有 service-instruction.ru 链接)
- [ ] 参考录音:社区 sample settings 对比(こいち時間 V2 对比贴、koichizikan 系列)
