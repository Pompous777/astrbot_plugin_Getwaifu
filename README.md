# astrbot_plugin_Getwaifu

当群友 `@机器人` 并发送 SFW 抽卡指令时，插件会调用对应接口拉图，先缓存到本地，再直接发送图片。

## 声明

- 本插件由 AI 助手生成与迭代。
- 本项目采用 `MIT License` 开源协议，详见 `LICENSE`。

## 功能

- 指令：`抽老婆` 以及一组 SFW 分类指令（见下方列表）
- 触发条件：消息中包含对机器人的 `@`
- 图片来源：
  - 大部分分类：`waifu.pics/sfw/{category}`
  - `抽老婆(waifu)`：`waifu.pics` 失败后自动切换 `waifu.im`、`nekos.best`
- 发送方式：本地缓存后通过图片消息发送（不直接回复 URL）
- 缓存清理：自动清理超过 24 小时的缓存图片（每 10 分钟最多执行一次清理）
- 失败兜底：接口异常时返回提示文本，不影响机器人主流程
- 事件传播：命中本插件指令后会 `stop_event()`，避免继续触发 LLM

## 安装

- 将插件目录放入 `AstrBot/data/plugins/`，或在 WebUI 上传 zip 安装
- 安装后重载插件即可使用

## 使用方式

在群里发送（推荐使用 `/` 前缀）：

- `@机器人 /抽老婆`
- `@机器人 /抽猫娘`
- `@机器人 /抽惠惠`
- `@机器人 /抽抱抱`

插件会回复：

- 一条文本（谁抽到了什么分类）
- 一张 SFW waifu 图片（来自本地缓存文件）

## 已支持的 SFW 指令

- `抽老婆` -> `waifu`
- `抽猫娘` -> `neko`
- `抽忍野忍` -> `shinobu`
- `抽惠惠` -> `megumin`
- `抽欺负` -> `bully`
- `抽贴贴` -> `cuddle`
- `抽哭哭` -> `cry`
- `抽抱抱` -> `hug`
- `抽嗷呜` -> `awoo`
- `抽亲亲` -> `kiss`
- `抽舔舔` -> `lick`
- `抽摸摸` -> `pat`
- `抽得意` -> `smug`
- `抽敲头` -> `bonk`
- `抽丢飞` -> `yeet`
- `抽脸红` -> `blush`
- `抽微笑` -> `smile`
- `抽挥手` -> `wave`
- `抽击掌` -> `highfive`
- `抽牵手` -> `handhold`
- `抽吃吃` -> `nom`
- `抽咬咬` -> `bite`
- `抽飞扑` -> `glomp`
- `抽巴掌` -> `slap`
- `抽处决` -> `kill`
- `抽飞踢` -> `kick`
- `抽开心` -> `happy`
- `抽眨眼` -> `wink`
- `抽戳戳` -> `poke`
- `抽跳舞` -> `dance`
- `抽嫌弃` -> `cringe`

## 说明

- 当前实现只返回 SFW 内容。
- 若无法识别机器人 QQ 号，插件会在存在 `@` 时默认放行处理，避免漏触发。
- 本地缓存目录在系统临时目录下：`astrbot_plugin_Getwaifu`。

## 参考

- AstrBot: https://github.com/AstrBotDevs/AstrBot
- AstrBot 插件开发文档: https://docs.astrbot.app/dev/star/plugin-new.html
- waifu.pics: https://waifu.pics/
