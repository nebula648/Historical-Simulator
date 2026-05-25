# ⏳ 历史模拟器 (Historical Simulator)

基于 LLM 的多时代历史推演沙盒。选择一个人物与时间节点，执掌一国，在 AI 驱动的无限可能性中重写人类历史的走向。

---

## ✨ 功能特性

- **多时代剧本切换** — 从公元前 264 年的布匿战争到公元 1805 年的拿破仑战争，横跨东西方十二个关键历史节点，一键载入不同时代的势力版图、资源分布与外交格局
- **政令推演系统** — 输入任意旨意（公开诏令/秘密行动），LLM 引擎依据当前世界状态与生效法则推演后果，包含数值变动、版图更迭、叙事生成与底层对账
- **动态 API Key 注入** — 玩家在侧边栏自主输入个人 API Key（支持 DeepSeek / Anthropic Claude / OpenAI / 自定义中转站），零环境依赖，密钥永不触碰 .env 或项目配置
- **异域 DLC 支持** — 内置罗马共和国、拿破仑法国等异域剧本，Echarts 地图自动适配中国/欧洲地理模板
- **蝴蝶效应引擎** — 基于触发条件的延迟连锁反应，模拟历史选择带来的长期后果
- **御前召见 & 宏观飞跃** — 与臣僚私密对话，或颁布长线国策飞跃数年，观察宏观历史变迁
- **硬熔断安全机制** — 未配置有效 Key 时，所有推演按钮物理锁死，杜绝消耗开发者额度

---

## 📦 安装与部署

### 环境要求

- Python ≥ 3.11
- pip

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/your-username/historical-simulator.git
cd historical-simulator

# 2. 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux / macOS
# venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动应用
streamlit run app.py
```

启动后浏览器自动打开 `http://localhost:8501`，在侧边栏「🔑 LLM 驱动引擎配置」中输入你的 API Key 即可开始游戏。

### 无需 .env 或 secrets.toml

本项目的硬熔断设计确保 **所有 API Key 仅保存在浏览器会话中**，不依赖 `.env` 文件、`st.secrets` 或任何环境变量。

---

## 🎮 快速开始

1. 打开应用，在侧边栏配置你的 LLM API Key
2. 从剧本卡片中选择一个时代（例如「赤壁之战」「崇祯十七年」「拿破仑战争」）
3. 点击「进入」载入剧本 —— 你会看到势力版图、资源面板与编年史
4. 在左侧政令面板中输入旨意（例如「整顿吏治，彻查各地贪腐」「命水师巡航长江，严防北军渡江」）
5. 点击「颁下圣旨」（或对应时代的按钮文案），观察 LLM 推演的结果
6. 使用「推进一月」进行时间流转，或「宏观飞跃」一次性跳转数年

---

## 🗺️ 当前剧本

| 时代 | 起始年份 | 剧本 ID |
|------|----------|----------|
| 罗马共和国 | 公元前 264 年 | `roman_republic_264bc` |
| 楚汉相争 | 公元前 206 年 | `chu_han_contention_206bc` |
| 汉武北伐 | 公元前 129 年 | `han_wu_northern_campaigns_129bc` |
| 赤壁之战 | 公元 208 年 | `red_cliffs_208ad` |
| 淝水之战 | 公元 383 年 | `battle_of_fei_river_383ad` |
| 安史之乱：帝国黄昏 | 公元 762 年 | `anshi_rebellion_762ad` |
| 靖康之耻 | 公元 1126 年 | `jingkang_1126` |
| 南宋：中兴与覆灭 | 公元 1260 年 | `southern_song_defense_1260ad` |
| 元灭南宋 | 公元 1276 年 | `yuan_conquest_1276` |
| 崇祯十七年 | 公元 1644 年 | `chongzhen_1644` |
| 三藩之乱 | 公元 1673 年 | `san_fan_rebellion_1673` |
| 拿破仑战争 | 公元 1805 年 | `napoleon_1805` |

---

## 🏗️ 项目结构

```
historical-simulator/
├── app.py                      # 入口：页面路由 + API Key 面板
├── requirements.txt            # Python 依赖
├── src/
│   ├── config/                 # 时代命名、资源定义等配置
│   ├── engine/                 # 核心数据结构 (Faction, GameState, MilitaryUnit)
│   ├── events/                 # 事件状态机、后果推演
│   ├── llm/                    # LLM 客户端 (DeepSeek/Anthropic/OpenAI/自定义)
│   ├── map/                    # Echarts 地图渲染、领土解析、时代地理清单
│   ├── scenario/               # 剧本加载器、Schema 校验
│   ├── session/                # Session 状态管理、快照与回滚
│   ├── simulation/             # 微推演、宏推演、御前召见
│   └── ui/                     # 画面板、编年史、事件对话框、剧本选择器
└── scenarios/
    ├── scenario_index.json     # 剧本索引（主数据源）
    ├── data/                   # 地理清单 manifest
    ├── 03_jin_sui_tang/        # 魏晋隋唐剧本
    ├── 04_song_yuan_ming/      # 宋元明剧本
    └── 99_foreign_dlc/         # 异域 DLC 剧本
```

---

## 🖼️ 截图

> *（使用中截图待补充）*

| 剧本选择页 | 游戏主界面 |
|:---:|:---:|
| ![剧本选择](screenshots/scenario_picker.png) | ![游戏主界面](screenshots/game_main.png) |

---

## 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源。

---

## ⚠️ 免责声明

本模拟器是纯粹的历史推演沙盒游戏。所有 LLM 生成的叙事内容均为虚构推演，不代表任何历史观点或政治立场。AI 生成内容可能存在事实性偏差，请以学术史料为准。
