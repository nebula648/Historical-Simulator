"""
Echarts 桥接层 —— 通过 st.iframe (data URI) 注入原生 Echarts
严禁使用 streamlit-echarts 库。
"""

from __future__ import annotations

import json
import base64
import streamlit as st

from src.map.region_mapper import (
    build_echarts_map_data,
    build_europe_map_data,
    get_faction_legend,
    REGION_TO_ECHARTS,
    ECHARTS_TO_REGIONS,
    EUROPE_REGION_TO_COUNTRY,
    COUNTRY_TO_EUROPE_REGIONS,
)


# Echarts CDN 资源
ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"
CHINA_MAP_CDN = "https://cdn.jsdelivr.net/npm/echarts@4.9.0/map/js/china.js"
WORLD_MAP_CDN = "https://cdn.jsdelivr.net/npm/echarts@4.9.0/map/js/world.js"

# 地图容器默认宽高
DEFAULT_WIDTH = "100%"
DEFAULT_HEIGHT = "600px"


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def render_strategic_map(
    territory: dict[str, str],
    factions: dict,
    width: str = DEFAULT_WIDTH,
    height: str = DEFAULT_HEIGHT,
) -> None:
    """
    渲染「天下大势」全局战略地图。

    参数:
        territory: {region_id: faction_id}
        factions: {faction_id: Faction}
        width, height: CSS 尺寸
    """
    map_template = st.session_state.get("map_template", "china")

    if map_template == "europe":
        _render_strategic_map_europe(territory, factions, width, height)
    else:
        _render_strategic_map_china(territory, factions, width, height)


def _render_strategic_map_china(
    territory: dict[str, str],
    factions: dict,
    width: str,
    height: str,
) -> None:
    """渲染中国地图模式。"""
    player_faction = st.session_state.get("player_faction", "")
    pf = factions.get(player_faction) if player_faction else None
    capital_region = pf.capital if pf else "北京"
    capital_province = REGION_TO_ECHARTS.get(capital_region)
    if capital_province is None:
        if capital_region in ECHARTS_TO_REGIONS:
            capital_province = capital_region
        else:
            capital_province = "北京"

    map_data = build_echarts_map_data(territory, factions, capital_province)
    legend = get_faction_legend(factions)

    era_label = "未知时代"
    try:
        from src.map.region_data_loader import get_current_era_label
        era_label = get_current_era_label()
    except Exception:
        pass

    html = _build_china_html(map_data, legend, capital_province, width, height, era_label)
    b64 = base64.b64encode(html.encode("utf-8")).decode("utf-8")
    data_uri = f"data:text/html;charset=utf-8;base64,{b64}"
    st.iframe(src=data_uri, height=int(height.replace("px", "")))


def _render_strategic_map_europe(
    territory: dict[str, str],
    factions: dict,
    width: str,
    height: str,
) -> None:
    """渲染欧洲/世界地图模式。"""
    player_faction = st.session_state.get("player_faction", "")
    pf = factions.get(player_faction) if player_faction else None
    capital_region = pf.capital if pf else "italia"
    capital_country = EUROPE_REGION_TO_COUNTRY.get(capital_region, "Italy")

    map_data = build_europe_map_data(territory, factions, capital_region)
    legend = get_faction_legend(factions)

    era_label = "未知时代"
    try:
        from src.map.region_data_loader import get_current_era_label
        era_label = get_current_era_label()
    except Exception:
        pass

    html = _build_europe_html(map_data, legend, capital_country, width, height, era_label)
    b64 = base64.b64encode(html.encode("utf-8")).decode("utf-8")
    data_uri = f"data:text/html;charset=utf-8;base64,{b64}"
    st.iframe(src=data_uri, height=int(height.replace("px", "")))


# ---------------------------------------------------------------------------
# HTML 模板构建
# ---------------------------------------------------------------------------

def _build_china_html(
    map_data: list[dict],
    legend: list[dict],
    capital_province: str,
    width: str,
    height: str,
    era_label: str = "",
) -> str:
    map_data_json = json.dumps(map_data, ensure_ascii=False)
    legend_json = json.dumps(legend, ensure_ascii=False)
    capital_province_json = json.dumps(capital_province, ensure_ascii=False)
    era_label_json = json.dumps(era_label, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{
            width: 100%; height: 100%;
            background: transparent;
            overflow: hidden;
        }}
        #map-container {{
            width: {width}; height: {height};
            margin: 0 auto;
        }}
        #legend-box {{
            position: absolute; bottom: 12px; left: 20px;
            display: flex; flex-wrap: wrap; gap: 10px;
            background: rgba(255,255,255,0.85);
            padding: 8px 14px; border-radius: 6px;
            z-index: 10;
            box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        }}
        .legend-item {{
            display: flex; align-items: center; gap: 6px;
            font-size: 13px; color: #333;
            font-family: 'Microsoft YaHei', sans-serif;
        }}
        .legend-dot {{
            width: 12px; height: 12px; border-radius: 2px;
        }}
    </style>
</head>
<body>
    <div id="map-container"></div>
    <div id="legend-box"></div>

    <script src="{ECHARTS_CDN}"></script>
    <script src="{CHINA_MAP_CDN}"></script>
    <script>
    (function() {{
        var chartDom = document.getElementById('map-container');
        var myChart = echarts.init(chartDom);

        var mapData = {map_data_json};
        var legendData = {legend_json};
        var eraLabel = {era_label_json};

        var option = {{
            backgroundColor: 'transparent',
            tooltip: {{
                trigger: 'item',
                backgroundColor: 'rgba(245, 240, 232, 0.97)',
                borderColor: '#C41E3A',
                borderWidth: 2,
                padding: 0,
                textStyle: {{ color: '#1A1A1A' }},
                formatter: function(params) {{
                    var name = params.name;
                    var item = null;
                    for (var i = 0; i < mapData.length; i++) {{
                        if (mapData[i].name === name) {{ item = mapData[i]; break; }}
                    }}
                    if (!item || !item.provinceStats) {{
                        return '<div style="padding:10px 14px;"><b>' + name + '</b></div>';
                    }}
                    var s = item.provinceStats;
                    var color = s.owner_color || '#888';
                    var popStr = s.population >= 100
                        ? (s.population / 100).toFixed(1) + ' 百万'
                        : s.population + ' 万';
                    var foodBar = '';
                    for (var j = 0; j < 10; j++) {{
                        foodBar += '<span style="display:inline-block;width:8px;height:8px;margin:0 1px;border-radius:1px;background:'
                            + (j < Math.round(s.food / 10) ? '#C4A43E' : '#E0D8C0') + ';"></span>';
                    }}
                    var stabBar = '';
                    for (var k = 0; k < 10; k++) {{
                        stabBar += '<span style="display:inline-block;width:8px;height:8px;margin:0 1px;border-radius:1px;background:'
                            + (k < Math.round(s.stability / 10) ? '#A0522D' : '#E0D8C0') + ';"></span>';
                    }}
                    var capitalBadge = s.is_capital
                        ? '<span style="display:inline-block;background:#FFD700;color:#8B0000;'
                            + 'font-size:10px;padding:2px 6px;border-radius:3px;margin-left:6px;'
                            + 'font-weight:bold;">⚜ 国都 · 皇帝行在</span>'
                        : '';
                    return '<div style="min-width:220px;font-family:\"Microsoft YaHei\",\"SimSun\",sans-serif;">'
                        + '<div style="background:linear-gradient(135deg,' + color + ' 0%,' + color + 'cc 100%);'
                        + 'color:#fff;padding:8px 14px;font-size:15px;font-weight:bold;">'
                        + s.ming_name + capitalBadge + '</div>'
                        + '<div style="padding:10px 14px;">'
                        + '<div style="font-size:11px;color:#999;margin-bottom:6px;">现代：' + name
                        + ' · 辖 ' + s.region_count + ' 区</div>'
                        + '<div style="border-top:1px solid #e0d8c8;margin:6px 0;"></div>'
                        + '<table style="width:100%;font-size:13px;line-height:2;">'
                        + '<tr><td style="color:#888;">👑 势力</td>'
                        + '<td style="font-weight:bold;color:' + color + ';">' + s.owner_name + '</td></tr>'
                        + '<tr><td style="color:#888;">👥 人口</td>'
                        + '<td style="font-weight:bold;">约 ' + popStr + ' 口</td></tr>'
                        + '<tr><td style="color:#888;">🌾 粮草</td>'
                        + '<td>' + foodBar + ' <b>' + s.food + '</b>/100</td></tr>'
                        + '<tr><td style="color:#888;">🏛️ 治安</td>'
                        + '<td>' + stabBar + ' <b>' + s.stability + '</b>/100</td></tr>'
                        + '</table>'
                        + '<div style=\"border-top:1px solid #e0d8c8;margin-top:6px;padding-top:4px;font-size:10px;color:#aaa;\">'
                        + '⏳ ' + eraLabel + '</div>'
                        + '</div></div>';
                }}
            }},
            geo: {{
                map: 'china',
                roam: true,
                zoom: 1.2,
                center: [105, 36],
                scaleLimit: {{ min: 0.8, max: 4 }},
                label: {{ show: false }},
                emphasis: {{
                    label: {{
                        show: true,
                        fontSize: 14,
                        fontWeight: 'bold',
                        color: '#333'
                    }},
                    itemStyle: {{ areaColor: '#E8E0D0' }}
                }},
                itemStyle: {{
                    areaColor: '#F0EDE5',
                    borderColor: '#C0B8A8',
                    borderWidth: 1
                }},
                regions: mapData
            }},
            series: [
                {{
                    type: 'map',
                    map: 'china',
                    geoIndex: 0,
                    data: mapData.map(function(d) {{ return {{ name: d.name, value: 1 }}; }})
                }}
            ]
        }};

        myChart.setOption(option);

        // ---- 绘制图例 ----
        var legendBox = document.getElementById('legend-box');
        legendData.forEach(function(item) {{
            var div = document.createElement('div');
            div.className = 'legend-item';
            div.innerHTML = '<span class="legend-dot" style="background:' + item.color
                + ';"></span>' + item.name + ' (' + item.regions + '区)';
            legendBox.appendChild(div);
        }});

        // ---- 响应式缩放 ----
        window.addEventListener('resize', function() {{
            myChart.resize();
        }});
    }})();
    </script>
</body>
</html>"""


def _build_europe_html(
    map_data: list[dict],
    legend: list[dict],
    capital_country: str,
    width: str,
    height: str,
    era_label: str = "",
) -> str:
    map_data_json = json.dumps(map_data, ensure_ascii=False)
    legend_json = json.dumps(legend, ensure_ascii=False)
    capital_json = json.dumps(capital_country, ensure_ascii=False)
    era_label_json = json.dumps(era_label, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{
            width: 100%; height: 100%;
            background: transparent;
            overflow: hidden;
        }}
        #map-container {{
            width: {width}; height: {height};
            margin: 0 auto;
        }}
        #legend-box {{
            position: absolute; bottom: 12px; left: 20px;
            display: flex; flex-wrap: wrap; gap: 10px;
            background: rgba(255,255,255,0.85);
            padding: 8px 14px; border-radius: 6px;
            z-index: 10;
            box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        }}
        .legend-item {{
            display: flex; align-items: center; gap: 6px;
            font-size: 13px; color: #333;
            font-family: 'Microsoft YaHei', sans-serif;
        }}
        .legend-dot {{
            width: 12px; height: 12px; border-radius: 2px;
        }}
    </style>
</head>
<body>
    <div id="map-container"></div>
    <div id="legend-box"></div>

    <script src="{ECHARTS_CDN}"></script>
    <script src="{WORLD_MAP_CDN}"></script>
    <script>
    (function() {{
        var chartDom = document.getElementById('map-container');
        var myChart = echarts.init(chartDom);

        var mapData = {map_data_json};
        var legendData = {legend_json};
        var capitalCountry = {capital_json};
        var eraLabel = {era_label_json};

        var option = {{
            backgroundColor: 'transparent',
            tooltip: {{
                trigger: 'item',
                backgroundColor: 'rgba(245, 240, 232, 0.97)',
                borderColor: '#8B0000',
                borderWidth: 2,
                padding: 0,
                textStyle: {{ color: '#1A1A1A' }},
                formatter: function(params) {{
                    var name = params.name;
                    var item = null;
                    for (var i = 0; i < mapData.length; i++) {{
                        if (mapData[i].name === name) {{ item = mapData[i]; break; }}
                    }}
                    if (!item || !item.provinceStats) {{
                        return '<div style="padding:10px 14px;"><b>' + name + '</b></div>';
                    }}
                    var s = item.provinceStats;
                    var color = s.owner_color || '#888';
                    var popStr = s.population >= 100
                        ? (s.population / 100).toFixed(1) + 'M'
                        : s.population + ' 万';
                    var foodBar = '';
                    for (var j = 0; j < 10; j++) {{
                        foodBar += '<span style="display:inline-block;width:8px;height:8px;margin:0 1px;border-radius:1px;background:'
                            + (j < Math.round(s.food / 10) ? '#C4A43E' : '#E0D8C0') + ';"></span>';
                    }}
                    var stabBar = '';
                    for (var k = 0; k < 10; k++) {{
                        stabBar += '<span style="display:inline-block;width:8px;height:8px;margin:0 1px;border-radius:1px;background:'
                            + (k < Math.round(s.stability / 10) ? '#A0522D' : '#E0D8C0') + ';"></span>';
                    }}
                    var capitalBadge = s.is_capital
                        ? '<span style="display:inline-block;background:#FFD700;color:#8B0000;'
                            + 'font-size:10px;padding:2px 6px;border-radius:3px;margin-left:6px;'
                            + 'font-weight:bold;">⚜ Capital</span>'
                        : '';
                    return '<div style="min-width:220px;font-family:\\"Microsoft YaHei\\",\\"SimSun\\",sans-serif;">'
                        + '<div style="background:linear-gradient(135deg,' + color + ' 0%,' + color + 'cc 100%);'
                        + 'color:#fff;padding:8px 14px;font-size:15px;font-weight:bold;">'
                        + s.ming_name + capitalBadge + '</div>'
                        + '<div style="padding:10px 14px;">'
                        + '<div style="font-size:11px;color:#999;margin-bottom:6px;">'
                        + 'Modern: ' + name + ' · ' + s.region_count + ' regions</div>'
                        + '<div style="border-top:1px solid #e0d8c8;margin:6px 0;"></div>'
                        + '<table style="width:100%;font-size:13px;line-height:2;">'
                        + '<tr><td style="color:#888;">⚡ Faction</td>'
                        + '<td style="font-weight:bold;color:' + color + ';">' + s.owner_name + '</td></tr>'
                        + '<tr><td style="color:#888;">👥 Population</td>'
                        + '<td style="font-weight:bold;">~' + popStr + '</td></tr>'
                        + '<tr><td style="color:#888;">🌾 Supply</td>'
                        + '<td>' + foodBar + ' <b>' + s.food + '</b>/100</td></tr>'
                        + '<tr><td style="color:#888;">🏛️ Stability</td>'
                        + '<td>' + stabBar + ' <b>' + s.stability + '</b>/100</td></tr>'
                        + '</table>'
                        + '<div style="border-top:1px solid #e0d8c8;margin-top:6px;padding-top:4px;font-size:10px;color:#aaa;">'
                        + '⏳ ' + eraLabel + '</div>'
                        + '</div></div>';
                }}
            }},
            geo: {{
                map: 'world',
                roam: true,
                zoom: 2.5,
                center: [12, 48],
                scaleLimit: {{ min: 1.0, max: 6 }},
                label: {{ show: false }},
                emphasis: {{
                    label: {{
                        show: true,
                        fontSize: 14,
                        fontWeight: 'bold',
                        color: '#333'
                    }},
                    itemStyle: {{ areaColor: '#E8E0D0' }}
                }},
                itemStyle: {{
                    areaColor: '#F0EDE5',
                    borderColor: '#888888',
                    borderWidth: 1
                }},
                regions: mapData
            }},
            series: [
                {{
                    type: 'map',
                    map: 'world',
                    geoIndex: 0,
                    data: mapData.map(function(d) {{ return {{ name: d.name, value: 1 }}; }})
                }}
            ]
        }};

        myChart.setOption(option);

        // ---- 绘制图例 ----
        var legendBox = document.getElementById('legend-box');
        legendData.forEach(function(item) {{
            var div = document.createElement('div');
            div.className = 'legend-item';
            div.innerHTML = '<span class="legend-dot" style="background:' + item.color
                + ';"></span>' + item.name + ' (' + item.regions + '区)';
            legendBox.appendChild(div);
        }});

        // ---- 响应式缩放 ----
        window.addEventListener('resize', function() {{
            myChart.resize();
        }});
    }})();
    </script>
</body>
</html>"""
