"""
时代名词映射系统
为 UI / LLM Prompt 提供按时代动态替换的术语表，消除硬编码朝代痕迹。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# 时代命名数据类
# ---------------------------------------------------------------------------

@dataclass
class EraNaming:
    """单个时代的全部 UI / Prompt 术语映射。"""
    era_key: str
    era_name: str                    # 时代名称：大明 / 大汉 / 汉末三国
    dynasty_name: str                # 朝代名：大明 / 大汉 / 汉
    power_center: str                # 侧边栏权力中枢标题
    intel_org: str                   # 情报机构全称：锦衣卫 / 绣衣使者 / 校事府
    intel_org_short: str             # 情报机构简称
    secret_action_label: str         # 秘密行动 radio 标签
    secret_action_desc: str          # 秘密行动 LLM 描述
    secret_action_placeholder: str   # 政令输入框占位文字示例
    default_capital: str             # 默认首都 region_id
    default_ruler: str               # 默认君主名（用于 prompt 空间锚定回退）
    default_courtiers: list[str]     # 默认朝臣列表
    llm_era_context: str             # LLM 系统提示词中的时代背景句
    llm_player_faction_desc: str     # LLM 提示中"玩家势力永远是 XXX"的描述
    correction_placeholder_lines: list[str]  # 纠错面板占位示例
    audience_placeholder: str        # 自定义召见对象 placeholder
    command_panel_gov_tab: str       # 政务选项卡标签
    command_panel_audience_tab: str  # 召见选项卡标签
    edict_button: str                # 呈递令旨按钮文字
    court_title: str                 # 朝堂/宫廷称谓


# ---------------------------------------------------------------------------
# 时代映射表
# ---------------------------------------------------------------------------

ERA_MAPPINGS: dict[str, EraNaming] = {
    # ---- 大明 / 明末清初 ----
    "ming": EraNaming(
        era_key="ming",
        era_name="大明",
        dynasty_name="大明",
        power_center="🏯 大明权力中枢",
        intel_org="锦衣卫",
        intel_org_short="锦衣卫",
        secret_action_label="🕵️ 密卫行动 (锦衣卫暗中执行)",
        secret_action_desc="锦衣卫/东厂暗中执行的任务（抄家、暗杀、刺探、策反等）",
        secret_action_placeholder="例如：传令锦衣卫抄没勋贵家产以充军饷...",
        default_capital="beijing",
        default_ruler="朱由检",
        default_courtiers=[
            "史可法", "马士英", "左良玉", "高杰", "黄得功",
            "刘良佐", "郑芝龙", "陈子龙", "孙传庭", "周遇吉",
        ],
        llm_era_context="崇祯十七年的明朝是默认背景，但世界法则可以改变一切。",
        llm_player_faction_desc='玩家势力永远是 "ming_empire"（大明帝国）。',
        correction_placeholder_lines=[
            "· 北京已陷落，不应作为大明首都",
            "· 左良玉已战死，不应出现",
            "· 大顺军主力已溃，不应再攻山西",
        ],
        audience_placeholder="请输入要宣召的姓名（如王承恩、锦衣卫指挥使或你的亲信）：",
        command_panel_gov_tab="📜 处理政务 (下达令旨)",
        command_panel_audience_tab="👥 御前召见 (角色互动)",
        edict_button="⚡ 呈递令旨",
        court_title="乾清宫东暖阁（或西苑平台）",
    ),

    # ---- 大汉 / 秦汉 ----
    "han": EraNaming(
        era_key="han",
        era_name="大汉",
        dynasty_name="大汉",
        power_center="🏯 大汉朝廷",
        intel_org="绣衣使者",
        intel_org_short="绣衣使者",
        secret_action_label="🕵️ 密使行动 (绣衣使者暗中执行)",
        secret_action_desc="绣衣使者/大谁何暗中执行的任务（刺探、策反、暗杀、直达天听等）",
        secret_action_placeholder="例如：遣绣衣使者潜入楚营策反楚将...",
        default_capital="chang_an",
        default_ruler="刘邦",
        default_courtiers=[
            "萧何", "张良", "韩信", "曹参", "陈平",
            "樊哙", "周勃", "夏侯婴", "灌婴", "郦食其",
        ],
        llm_era_context="秦末汉初的天下格局是默认背景，但世界法则可以改变一切。",
        llm_player_faction_desc='玩家势力由其 faction_id 标识（如 "han" 大汉）。',
        correction_placeholder_lines=[
            "· 咸阳已被项羽焚毁，不应作为大汉都城",
            "· 韩信已受封齐王，不应以普通将领身份出现",
            "· 九江王英布已叛楚归汉，不应再列为楚军",
        ],
        audience_placeholder="请输入要宣召的姓名（如萧何、张良或绣衣使者）：",
        command_panel_gov_tab="📜 处理政务 (下达诏令)",
        command_panel_audience_tab="👥 召对问策 (君臣密议)",
        edict_button="⚡ 呈递诏令",
        court_title="未央宫前殿（或温室殿）",
    ),

    # ---- 东晋十六国 / 淝水之战 ----
    "jin": EraNaming(
        era_key="jin",
        era_name="东晋十六国",
        dynasty_name="大晋",
        power_center="🏯 大晋朝廷（建康台城）",
        intel_org="台使·典签",
        intel_org_short="台使",
        secret_action_label="🕵️ 台使刺奸 (典签暗中密报)",
        secret_action_desc="台使/典签暗中执行的任务（监视方镇、刺探军情、密奏弹劾等）",
        secret_action_placeholder="例如：遣台使典签密查北府诸将动静...",
        default_capital="jiankang",
        default_ruler="司马曜",
        default_courtiers=[
            "谢安", "谢玄", "刘牢之", "桓冲", "谢石",
            "王坦之", "郗超", "桓伊", "朱序", "毛宝",
        ],
        llm_era_context="东晋太元八年的南北对峙格局是默认背景，但世界法则可以改变一切。",
        llm_player_faction_desc='玩家势力由其 faction_id 标识（如 "eastern_jin" 大晋）。',
        correction_placeholder_lines=[
            "· 建康（南京）是大晋京师，非普通州郡",
            "· 谢玄已受命组建北府兵，不应以普通将领身份出现",
            "· 苻坚大军尚未渡淮，不应突然出现在长江南岸",
        ],
        audience_placeholder="请输入要召见的姓名（如谢安、谢玄或台使典签）：",
        command_panel_gov_tab="📜 处理朝政 (尚书台行文)",
        command_panel_audience_tab="👥 台城召对 (君臣清谈)",
        edict_button="⚡ 下达台敕",
        court_title="建康台城（或乌衣巷谢府）",
    ),

    # ---- 盛唐 / 安史之乱 ----
    "tang": EraNaming(
        era_key="tang",
        era_name="盛唐",
        dynasty_name="大唐",
        power_center="🏯 大唐权力中枢（大明宫）",
        intel_org="不良人/内卫",
        intel_org_short="不良人",
        secret_action_label="🕵️ 内卫缉捕 (不良人暗中查访)",
        secret_action_desc="不良人/内卫暗中执行的任务（查访、缉捕、刺探、策反等）",
        secret_action_placeholder="例如：命不良人暗中查访范阳节度使府动静...",
        default_capital="chang_an",
        default_ruler="李隆基",
        default_courtiers=[
            "郭子仪", "李光弼", "哥舒翰", "封常清", "高仙芝",
            "张巡", "颜真卿", "许远", "仆固怀恩", "李泌",
        ],
        llm_era_context="天宝十四年的大唐盛世是默认背景，但世界法则可以改变一切。",
        llm_player_faction_desc='玩家势力由其 faction_id 标识（如 "tang_empire" 大唐帝国）。',
        correction_placeholder_lines=[
            "· 范阳是安禄山叛军大本营，不应仍属朝廷控制",
            "· 杨国忠与哥舒翰不和，不可联名上奏",
            "· 潼关若失守，长安危在旦夕，不可假设固若金汤",
        ],
        audience_placeholder="请输入要召见的姓名（如郭子仪、高力士或不良帅）：",
        command_panel_gov_tab="📜 处理朝政 (中书门下敕旨)",
        command_panel_audience_tab="👥 延英召对 (宰臣议政)",
        edict_button="⚡ 颁下敕旨",
        court_title="大明宫宣政殿（或兴庆宫南薰殿）",
    ),

    # ---- 汉末 / 三国 ----
    "three_kingdoms": EraNaming(
        era_key="three_kingdoms",
        era_name="汉末三国",
        dynasty_name="大汉（汉室）",
        power_center="🏯 霸府·军师祭酒",
        intel_org="校事府",
        intel_org_short="校事",
        secret_action_label="🕵️ 秘计行动 (校事府暗中执行)",
        secret_action_desc="校事府/刺奸屯暗中执行的任务（刺探、离间、策反、暗杀等）",
        secret_action_placeholder="例如：命校事府密探潜入曹营散布流言...",
        default_capital="jiangling",
        default_ruler="刘备",
        default_courtiers=[
            "诸葛亮", "关羽", "张飞", "赵云", "马超",
            "黄忠", "魏延", "庞统", "法正", "马谡",
        ],
        llm_era_context="建安十三年的汉末乱世是默认背景，但世界法则可以改变一切。",
        llm_player_faction_desc='玩家势力由其 faction_id 标识（如 "shu" 蜀汉、"wei" 曹魏、"wu" 东吴）。',
        correction_placeholder_lines=[
            "· 刘琮已降曹，荆州不应再属刘表",
            "· 曹操主力在江陵，不应突然出现在柴桑",
            "· 周瑜与程普有隙，水军指挥权尚未统一",
        ],
        audience_placeholder="请输入要召见的姓名（如诸葛亮、庞统或校事府密探）：",
        command_panel_gov_tab="📜 处理军政 (下达军令)",
        command_panel_audience_tab="👥 升帐议事 (文武合议)",
        edict_button="⚡ 传令三军",
        court_title="左将军府（或公安行营）",
    ),

    # ---- 北宋 / 靖康之耻 ----
    "song": EraNaming(
        era_key="song",
        era_name="北宋末年",
        dynasty_name="大宋",
        power_center="🏯 大宋朝廷（东京开封府）",
        intel_org="皇城司",
        intel_org_short="皇城司",
        secret_action_label="🕵️ 皇城探事 (皇城司暗中察访)",
        secret_action_desc="皇城司/走马承受暗中执行的任务（刺探、监察、反间、密奏等）",
        secret_action_placeholder="例如：遣皇城司探子密查金营虚实...",
        default_capital="河南",
        default_ruler="赵佶",
        default_courtiers=[
            "李纲", "宗泽", "种师道", "张叔夜", "姚平仲",
            "韩世忠", "岳飞", "刘韐", "折彦质", "秦桧",
        ],
        llm_era_context="宣和七年·靖康元年的宋金对峙是默认背景，但世界法则可以改变一切。",
        llm_player_faction_desc='玩家势力由其 faction_id 标识（如 "northern_song" 大宋）。',
        correction_placeholder_lines=[
            "· 太原尚未陷落，不应假设金军已渡黄河",
            "· 种师道正率西军勤王，不应忽略这支力量",
            "· 汴京三重城防尚未被攻破，不应假设城陷",
        ],
        audience_placeholder="请输入要召见的姓名（如李纲、宗泽或皇城司都知）：",
        command_panel_gov_tab="📜 处理朝政 (尚书省札子)",
        command_panel_audience_tab="👥 垂拱召对 (经筵密议)",
        edict_button="⚡ 批下御笔",
        court_title="东京大内垂拱殿（或延和殿）",
    ),

    # ---- 元朝 / 灭南宋 ----
    "yuan": EraNaming(
        era_key="yuan",
        era_name="元朝·至元年间",
        dynasty_name="大元",
        power_center="🏯 大元朝廷（大都·汗廷）",
        intel_org="大都监察司",
        intel_org_short="监察司",
        secret_action_label="🕵️ 监察刺探 (大都监察司暗中查访)",
        secret_action_desc="大都监察司/御史台暗中执行的任务（监视汉臣、刺探南宋、查抄逆产等）",
        secret_action_placeholder="例如：命大都监察司查访江南归附州县动向...",
        default_capital="北京",
        default_ruler="忽必烈",
        default_courtiers=[
            "伯颜", "阿术", "张弘范", "吕文焕", "史天泽",
            "刘整", "廉希宪", "安童", "董文炳", "张柔",
        ],
        llm_era_context="至元十三年·元灭南宋之役是默认背景，但世界法则可以改变一切。",
        llm_player_faction_desc='玩家势力由其 faction_id 标识（如 "yuan_empire" 大元帝国）。',
        correction_placeholder_lines=[
            "· 襄阳已降元，不应再出现宋军固守襄阳的描述",
            "· 伯颜主力在长江北岸，水军尚未渡江",
            "· 临安三面被围，海路是唯一退路",
        ],
        audience_placeholder="请输入要召见的姓名（如伯颜、张弘范或大都监察使）：",
        command_panel_gov_tab="📜 处理政务 (中书省札付)",
        command_panel_audience_tab="👥 内廷召对 (枢密院军事会议)",
        edict_button="⚡ 颁下圣旨",
        court_title="大都皇城大明殿（或上都开平府）",
    ),

    # ---- 晚清 / 甲午战争 ----
    "qing": EraNaming(
        era_key="qing",
        era_name="晚清·光绪朝",
        dynasty_name="大清",
        power_center="🏯 大清朝廷（京师·颐和园/军机处）",
        intel_org="总理衙门/北洋探报",
        intel_org_short="北洋探报",
        secret_action_label="🕵️ 密探外报 (北洋探报暗中侦察)",
        secret_action_desc="北洋水师探报/总理衙门暗中执行的任务（外情刺探、海防监察、条约密使等）",
        secret_action_placeholder="例如：令北洋水师密探监视日本舰队动向...",
        default_capital="北京",
        default_ruler="载湉",
        default_courtiers=[
            "李鸿章", "张之洞", "左宝贵", "邓世昌", "丁汝昌",
            "刘步蟾", "袁世凯", "翁同龢", "刘铭传", "聂士成",
        ],
        llm_era_context="光绪二十年·甲午战争前夕是默认背景，但世界法则可以改变一切。",
        llm_player_faction_desc='玩家势力由其 faction_id 标识（如 "qing_empire" 大清帝国）。',
        correction_placeholder_lines=[
            "· 北洋水师定远镇远两舰尚在，不应假设舰队已覆灭",
            "· 朝鲜东学党起义是战争导火索，不应忽略",
            "· 日本联合舰队尚未取得黄海制海权",
        ],
        audience_placeholder="请输入要召见的姓名（如李鸿章、邓世昌或北洋探报委员）：",
        command_panel_gov_tab="📜 处理政务 (军机处电旨)",
        command_panel_audience_tab="👥 军机召对 (北洋会办)",
        edict_button="⚡ 电传谕旨",
        court_title="颐和园仁寿殿（或紫禁城乾清宫）",
    ),

    # ---- 清初·康熙朝 / 三藩之乱 ----
    "qing_early": EraNaming(
        era_key="qing_early",
        era_name="清初·康熙朝",
        dynasty_name="大清",
        power_center="🏯 大清朝廷（北京·乾清宫/南书房）",
        intel_org="粘杆处",
        intel_org_short="粘杆处",
        secret_action_label="🕵️ 密折奏事 (粘杆处暗中查访)",
        secret_action_desc="粘杆处/御前侍卫暗中执行的任务（监视藩王、刺探军情、密折奏报等）",
        secret_action_placeholder="例如：命粘杆处暗中查访平西王府动静...",
        default_capital="北京",
        default_ruler="爱新觉罗·玄烨",
        default_courtiers=[
            "图海", "索额图", "明珠", "熊赐履", "李光地",
            "施琅", "姚启圣", "于成龙", "靳辅", "周培公",
            "杰书", "勒尔锦", "张勇", "蔡毓荣", "赵良栋",
        ],
        llm_era_context="康熙十二年·三藩之乱前夕是默认背景，但世界法则可以改变一切。",
        llm_player_faction_desc='玩家势力由其 faction_id 标识（如 "wu_sangui" 平西王、"qing_empire" 大清帝国）。',
        correction_placeholder_lines=[
            "· 吴三桂尚未正式举兵反清，不应假设已开战",
            "· 耿精忠、尚之信各有盘算，不可假设必会响应",
            "· 康熙帝年方弱冠，但已显露雄主之姿，不可轻视",
            "· 关宁铁骑是吴三桂的王牌，不可在非关键战役中折损",
        ],
        audience_placeholder="请输入要召见的姓名（如方光琛、胡国柱或粘杆处侍卫）：",
        command_panel_gov_tab="📜 处理政务 (藩王府谕令)",
        command_panel_audience_tab="👥 王府议政 (幕僚密议)",
        edict_button="⚡ 下达谕令",
        court_title="平西王府·五华山银安殿（或昆明城内藩署）",
    ),

    # ---- 罗马共和国 / 布匿战争前夕 ----
    "rome": EraNaming(
        era_key="rome",
        era_name="罗马共和国",
        dynasty_name="SPQR（元老院与罗马人民）",
        power_center="🏯 罗马元老院（Curia Hostilia）",
        intel_org="Frumentarii（罗马密探）",
        intel_org_short="Frumentarii",
        secret_action_label="🕵️ 密探行动 (Frumentarii暗中侦察)",
        secret_action_desc="Frumentarii/Speculatores暗中执行的任务（刺探、策反、暗杀、军粮情报等）",
        secret_action_placeholder="例如：遣Frumentarii密探潜入迦太基城刺探军情...",
        default_capital="italia",
        default_ruler="（元老院与执政官）",
        default_courtiers=[
            "费边·马克西穆斯", "西庇阿", "雷古鲁斯", "弗拉米尼乌斯",
            "克劳狄乌斯·马尔凯鲁斯", "保卢斯", "瓦罗", "尼禄",
            "梅特卢斯", "杜伊利乌斯",
        ],
        llm_era_context="公元前264年·第一次布匿战争前夕的地中海世界是默认背景，但世界法则可以改变一切。",
        llm_player_faction_desc='玩家势力由其 faction_id 标识（如 "roman_republic" SPQR）。',
        correction_placeholder_lines=[
            "· 迦太基海军控制西地中海，不应假设罗马已取得制海权",
            "· 执政官每年轮换，不应让同一人连续统帅",
            "· 西西里岛是争议焦点，不可忽略此战略要地",
        ],
        audience_placeholder="请输入要召见的元老或将领（如费边·马克西穆斯或Frumentarii探员）：",
        command_panel_gov_tab="📜 元老院提案 (Senatus Consultum)",
        command_panel_audience_tab="👥 执政官召见 (Consilium)",
        edict_button="⚡ 颁布元老院决议",
        court_title="罗马广场·元老院（Curia Hostilia）",
    ),

    # ---- 拿破仑战争 / 法兰西第一帝国 ----
    "napoleon": EraNaming(
        era_key="napoleon",
        era_name="拿破仑时代",
        dynasty_name="法兰西帝国",
        power_center="🏯 杜伊勒里宫·帝国大本营",
        intel_org="帝国宪兵队（Gendarmerie Impériale）",
        intel_org_short="帝国宪兵队",
        secret_action_label="🕵️ 宪兵密探 (帝国宪兵队暗中执行)",
        secret_action_desc="帝国宪兵队/情报局暗中执行的任务（反间谍、监视占领区、策反敌将等）",
        secret_action_placeholder="例如：命帝国宪兵队暗中监视奥地利使馆动向...",
        default_capital="france",
        default_ruler="拿破仑·波拿巴",
        default_courtiers=[
            "塔列朗", "富歇", "达武", "缪拉", "内伊",
            "苏尔特", "贝尔纳多特", "拉纳", "贝蒂埃", "拉萨尔",
        ],
        llm_era_context="1805年·第三次反法同盟战争前夕的欧洲是默认背景，但世界法则可以改变一切。",
        llm_player_faction_desc='玩家势力由其 faction_id 标识（如 "french_empire" 法兰西帝国）。',
        correction_placeholder_lines=[
            "· 英国皇家海军控制英吉利海峡，不应假设已成功登陆英国",
            "· 奥地利与俄罗斯正在组建联军，不可忽略东线威胁",
            "· 特拉法加海战尚未发生，法国-西班牙联合舰队尚在",
        ],
        audience_placeholder="请输入要召见的元帅或大臣（如达武元帅、富歇警务大臣）：",
        command_panel_gov_tab="📜 皇帝敕令 (Décret Impérial)",
        command_panel_audience_tab="👥 元帅会议 (Conseil de Guerre)",
        edict_button="⚡ 签署敕令",
        court_title="杜伊勒里宫（或枫丹白露宫）",
    ),
}

# 默认回退时代（当 session 中没有正确设置 era_key 时使用）
_DEFAULT_ERA = "ming"


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def get_era_naming(era_key: str | None = None) -> EraNaming:
    """
    获取指定时代的术语映射。未传入 era_key 时从 session_state 读取。

    支持 per-scenario era_metadata 覆盖：若 session_state 中存在
    era_power_center_override / era_intel_org_override，
    则用 dataclasses.replace 创建一份运行时副本，不影响全局映射表。

    参数:
        era_key: 时代标识符（如 "ming", "han", "three_kingdoms"）

    返回:
        EraNaming 实例（可能被 per-scenario 覆盖）
    """
    if era_key is None:
        import streamlit as st
        era_key = st.session_state.get("era_key", _DEFAULT_ERA)

    base = ERA_MAPPINGS.get(era_key, ERA_MAPPINGS[_DEFAULT_ERA])

    # 检查 per-scenario 覆盖
    try:
        import streamlit as st
        overrides: dict[str, Any] = {}

        power_override = st.session_state.get("era_power_center_override")
        if power_override:
            overrides["power_center"] = power_override

        intel_override = st.session_state.get("era_intel_org_override")
        if intel_override:
            overrides["intel_org"] = intel_override
            overrides["intel_org_short"] = intel_override
            overrides["secret_action_label"] = f"🕵️ 密卫行动 ({intel_override}暗中执行)"
            overrides["secret_action_desc"] = f"{intel_override}暗中执行的任务"
            overrides["secret_action_placeholder"] = f"例如：命{intel_override}暗中查访..."
            overrides["audience_placeholder"] = f"请输入要召见的姓名（或{intel_override}探员）："

        if overrides:
            from dataclasses import replace
            return replace(base, **overrides)
    except Exception:
        pass

    return base


def get_era_naming_safe(era_key: str | None = None) -> EraNaming:
    """
    与 get_era_naming 相同，但不依赖 streamlit（可用于模块加载阶段）。
    仅在无法访问 session_state 时使用。
    """
    if era_key is None:
        try:
            import streamlit as st
            era_key = st.session_state.get("era_key", _DEFAULT_ERA)
        except Exception:
            era_key = _DEFAULT_ERA
    return ERA_MAPPINGS.get(era_key, ERA_MAPPINGS[_DEFAULT_ERA])


def has_intel_org(era: EraNaming | None = None) -> bool:
    """当前时代是否有情报机构。"""
    if era is None:
        era = get_era_naming()
    return bool(era.intel_org and era.intel_org.strip())


def list_era_keys() -> list[str]:
    """返回所有已注册的时代标识符列表。"""
    return list(ERA_MAPPINGS.keys())


def register_era(era: EraNaming) -> None:
    """动态注册一个新的时代映射（用于扩展）。"""
    ERA_MAPPINGS[era.era_key] = era
