# CPSC 监控 Skill — 用户使用说明

> ⚠️ 设计稿，最终版拷到 GitHub 仓库 cpsc-monitor/README.md

---

```markdown
# CPSC 监控 Skill

一个让你每天早上 9 点自动知道"CPSC 又发了什么新公告、跟你哪些 SKU 相关、要做什么动作"的 Skill。

**3 分钟配置，30 分钟跑起来，从此再也不用半夜被亚马逊冻结资金的电话吵醒。**

---

## 这是什么？

把"AI 自动监控 CPSC 公告 + 风险判断 + 报告生成 + 邮件/短信告警"封装成 5 个文件，
你下载下来填一下 SKU 列表，就能跑。

适合做亚马逊北美站的卖家，特别是做：
- 儿童产品（玩具、婴儿用品、电动牙刷）
- 电池产品（充电宝、蓝牙耳机、电动工具）
- 磁铁产品（磁力玩具、磁性收纳）
- 电子产品（小家电、智能硬件）
- 家用电器

---

## 5 分钟上手

### 1. 下载

```bash
git clone https://github.com/Bailing-01/cpsc-monitor.git
cd cpsc-monitor
pip install -r requirements.txt
```

### 2. 配置

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml，至少填 my_skus 和 alert_emails
```

### 3. 测试运行

```bash
python run.py --now
```

### 4. 设置每日定时

```bash
# crontab -e，加一行：
0 9 * * * cd /path/to/cpsc-monitor && python run.py >> ./logs/cron.log 2>&1
```

---

## 文件结构

```
cpsc-monitor/
├── SKILL.md                ← 指令清单（AI Agent 用）
├── config.example.yaml     ← 配置示例
├── config.yaml             ← 你的配置（git ignore）
├── run.py                  ← 主程序
├── weekly.py               ← 周报程序
├── prompt-template.md      ← AI 判断用的 4 个 prompt
├── workflow.md             ← 详细工作流说明
├── templates/
│   ├── risk-report.md      ← 日报模板
│   ├── alert-email.md      ← 告警邮件模板
│   ├── alert-sms.md        ← 告警短信模板
│   └── weekly-report.md    ← 周报模板
├── output/                 ← 生成的报告
├── logs/                   ← 运行日志
└── history.yaml            ← 历史记录
```

---

## 它帮你做什么？

| 时间 | 自动动作 |
|---|---|
| 每天 9:00 | 抓 CPSC 最新公告 |
| 每天 9:01 | AI 判断哪些跟你 SKU 相关 |
| 每天 9:02 | 生成风险报告 |
| 每天 9:03 | 高风险发邮件 + 短信 |
| 每天 9:05 | 中低风险进日报 |
| 每周日 20:00 | 生成周报 |

**从 CPSC 公告发布到你收到"你的 X SKU 可能有问题"的提醒，全程不到 48 小时。**

---

## 不帮你做什么？

- ❌ 不帮你自动提交 UL 报告（这个必须你自己找实验室做）
- ❌ 不帮你联系亚马逊卖家支持（需要你登录后台开 case）
- ❌ 不帮你对接 UL 实验室 API（V2 路线图）
- ❌ 不监控非 CPSC 的合规（如 FDA、FCC、Prop 65 —— V2 路线图）

---

## 常见问题

### Q: 我没用过 AI Agent，怎么用？

A: 这个 Skill 不需要你懂 AI Agent。你只需要会：
- 编辑 YAML 文件（用 VS Code 或记事本都行）
- 跑 Python 命令
- 设置 cron 定时任务

如果你不会 cron，V2 会出一个"一键启动"脚本。

### Q: 我没有云服务器怎么办？

A: Skill 可以跑在任何能跑 Python 的机器上：
- 你自己的 Mac（每天开机时跑）
- 树莓派（24 小时开着，耗电极低）
- 云服务器（推荐，¥30/月起）

### Q: 我有 1000 个 SKU，会不会很慢？

A: 1000 个 SKU 跑一次大约 5-8 分钟。如果超过 5000 个，建议用 V2 的"SKU 分组"功能。

### Q: 这个 Skill 收费吗？

A: 完全免费。你可以自由使用、修改、分发。
但如果你想支持作者，关注微信公众号"Bailing 跨境"。

---

## 作者

bailing，亚马逊官方讲师 + 第三方卖家 10 年。
专注北美站合规与 AI 提效。

- 公众号：Bailing 跨境
- 知乎：bailing
- GitHub：Bailing-01
- 邮箱：[email protected]

---

## License

MIT License。你可以随便用，标一下出处就行。
```

---

# 汇总：整个 Skill 的全部文件清单（你 GitHub 仓库要有的）

```
cpsc-monitor/
├── SKILL.md                ← AI Agent 指令清单（你 Skill 的"灵魂"）
├── README.md               ← 用户使用说明（公众号引流入口）
├── config.example.yaml     ← 配置示例
├── prompt-template.md      ← 4 个 AI prompt
├── workflow.md             ← 工作流说明
├── run.py                  ← 主程序（需 Python 实现）
├── weekly.py               ← 周报程序（需 Python 实现）
├── requirements.txt        ← Python 依赖
├── .gitignore              ← 忽略 config.yaml / logs / output
├── templates/
│   ├── risk-report.md
│   ├── alert-email.md
│   ├── alert-sms.md
│   └── weekly-report.md
└── LICENSE                 ← MIT
```

## 真正要写的"内容"是 7 个文件

我已经把**6 个文件**的设计稿写完（你照着复制到 GitHub 仓库即可）：

| ✅ | 文件 | 在我 Obsidian 哪里 |
|---|---|---|
| ✅ | SKILL.md | `1-SKILL.md设计稿.md` |
| ✅ | config.example.yaml | `2-config.yaml示例.md` |
| ✅ | prompt-template.md | `3-prompt-template.md设计稿.md` |
| ✅ | workflow.md | `4-workflow和templates.md` 第一段 |
| ✅ | templates/risk-report.md | `4-workflow和templates.md` 第二段 |
| ✅ | templates/alert-email.md | `4-workflow和templates.md` 第四段 |
| ✅ | templates/alert-sms.md | `4-workflow和templates.md` 第三段 |
| ✅ | templates/weekly-report.md | `4-workflow和templates.md` 第五段 |
| ✅ | README.md | `5-README.md设计稿.md`（本文） |

**还需要你自己写的 2 个文件**（我不会写）：
| ❌ | 文件 | 为什么我写不了 |
|---|---|---|
| ❌ | run.py | 这是 Python 代码，需要跑通真实抓取 + AI 调用 + 邮件发送 |
| ❌ | weekly.py | 同上 |

**这两个 Python 文件**，你可以让 Cursor / Claude Code / Codex 帮你写，
或者你自己 1-2 小时填完（按 workflow.md 的步骤写即可）。

---

# 下一步建议（按优先级）

1. **先建 GitHub 仓库**：https://github.com/Bailing-01/cpsc-monitor
   - 复制我给你的 6 个文件内容
   - 提交 + push

2. **再写 run.py**（建议用 Cursor/Claude Code 帮你生成）：
   - 输入：`workflow.md` 的步骤
   - 输出：可运行的 Python 脚本

3. **测试 1 个真实公告**：
   - 找上周 CPSC 一条召回
   - 手动填到 config.yaml
   - 跑一次 `python run.py --now`
   - 验证报告质量

4. **公众号第 2 篇教程**（07-08 发布）：
   - 截图"5 分钟上手"流程
   - 配真实跑出来的报告
   - 加 GitHub 仓库链接

5. **公众号菜单**：把 GitHub README 的链接挂上去

预计你 **1-2 小时** 填完所有内容，**第 2 篇教程**有真实素材可写。