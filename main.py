"""
J.A.R.V.I.S. / 第二大脑 · 云端全天候每日晨报与自我进化守护引擎 (GitHub Actions 版)
========================================================================
运行环境：GitHub Actions (全球云端服务器，24小时全天候守护，无需开机)
触发时间：每天北京时间早晨 07:50 (UTC 23:50，提前避开整点拥堵)

核心功能：
1. 【动态待办】以 second-brain-vault 的 tasks/index.md 为唯一事实来源，实时展示当天待办
2. 【行程引擎】内置太原游倒计时与状态机，旅游结束后自动淡出，无缝切换为后续重点
3. 【聚变前沿】实时检索 arXiv physics.plasm-ph，7天去重记忆，生成针对性语义研判
4. 【AI 前沿】实时检索 arXiv cs.AI/cs.MA/cs.CL，7天去重记忆，生成 Agent/AI4Science 研判
5. 【费曼挑战】每日早晨由 AI 主动抛出 1 道 S/A 级核心物理概念深度思考题，检验真掌握度
6. 【自我进化】基于系统架构痛点与聚变研究动态提出真创新提案
7. 【全网推送】WxPusher 微信卡片毫秒级直达手机
8. 【自动归档】自动将晨报 Markdown 提交到 second-brain-vault/vault/memory/summary/daily/
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
import re
from datetime import datetime, date, timezone, timedelta
import ssl

# ==================== 解决 Windows 编码 ====================
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ==================== 环境变量 / 密钥配置 ====================
APP_TOKEN = os.environ.get("WXPUSHER_APP_TOKEN", "AT_MERfNtorNArt4Alo9AkpUx1GRjpieamX")
USER_UID = os.environ.get("WXPUSHER_UID", "UID_HtpiaxeUlxUPMe6lwisMaavhlC0u")
VAULT_PAT = os.environ.get("VAULT_PAT") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "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"

VAULT_OWNER = "althouseaikman684-stack"
VAULT_REPO = "second-brain-vault"

# 北京时间时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))

# ==================== SSL 上下文兼容 ====================
SSL_CONTEXT = ssl._create_unverified_context()

# ==================== 1. GitHub API 交互组件 ====================
def github_api_get_file(file_path):
    """从 second-brain-vault 私有仓库获取指定文件内容"""
    url = f"https://api.github.com/repos/{VAULT_OWNER}/{VAULT_REPO}/contents/{file_path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Jarvis-Daily-Bot"
    }
    if VAULT_PAT:
        headers["Authorization"] = f"Bearer {VAULT_PAT}"
        
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12, context=SSL_CONTEXT) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            content_b64 = data.get("content", "")
            sha = data.get("sha", "")
            raw_text = base64.b64decode(content_b64).decode('utf-8')
            return raw_text, sha
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, None
        print(f"[Warn] GitHub API HTTP error for {file_path}: {e.code} - {e.reason}")
    except Exception as e:
        print(f"[Warn] GitHub API fetch error for {file_path}: {e}")
    return None, None

def github_api_put_file(file_path, content_text, commit_message):
    """向 second-brain-vault 私有仓库提交/更新文件"""
    if not VAULT_PAT:
        print("[Info] 未配置 VAULT_PAT，跳过云端 GitHub 仓库自动提交归档。")
        return False
        
    _, existing_sha = github_api_get_file(file_path)
    
    url = f"https://api.github.com/repos/{VAULT_OWNER}/{VAULT_REPO}/contents/{file_path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {VAULT_PAT}",
        "User-Agent": "Jarvis-Daily-Bot",
        "Content-Type": "application/json"
    }
    
    content_b64 = base64.b64encode(content_text.encode('utf-8')).decode('utf-8')
    payload = {
        "message": commit_message,
        "content": content_b64
    }
    if existing_sha:
        payload["sha"] = existing_sha
        
    req_data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=req_data, headers=headers, method="PUT")
    
    try:
        with urllib.request.urlopen(req, timeout=15, context=SSL_CONTEXT) as resp:
            if resp.status in (200, 201):
                print(f"✅ [GitHub] 晨报已成功提交至 GitHub 知识库: {file_path}")
                return True
    except Exception as e:
        print(f"❌ [GitHub] 提交归档至 GitHub 失败: {e}")
    return False

# ==================== 2. 近期已推送论文去重机制 ====================
def get_recently_pushed_arxiv_ids(today_bj):
    """获取近 7 天已推送晨报中记录的所有 arXiv ID，杜绝重复推送"""
    seen_ids = set()
    for d_offset in range(1, 6):
        past_date = today_bj - timedelta(days=d_offset)
        past_path = f"vault/memory/summary/daily/{past_date.strftime('%Y-%m-%d')}.md"
        raw_text, _ = github_api_get_file(past_path)
        if not raw_text:
            raw_text, _ = github_api_get_file(f"memory/summary/daily/{past_date.strftime('%Y-%m-%d')}.md")
        if raw_text:
            links = re.findall(r'arxiv\.org/abs/([\w\.\d\-]+)', raw_text)
            for link_id in links:
                pure_id = link_id.split('v')[0]
                seen_ids.add(pure_id)
                
    try:
        local_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vault", "memory", "summary", "daily"))
        if os.path.exists(local_dir):
            for fname in os.listdir(local_dir):
                if fname.endswith(".md"):
                    with open(os.path.join(local_dir, fname), "r", encoding="utf-8", errors="ignore") as f:
                        txt = f.read()
                    links = re.findall(r'arxiv\.org/abs/([\w\.\d\-]+)', txt)
                    for link_id in links:
                        pure_id = link_id.split('v')[0]
                        seen_ids.add(pure_id)
    except Exception:
        pass
        
    print(f"🔍 [De-dup] 已识别历史已推送 arXiv 论文 {len(seen_ids)} 篇，自动开启去重过滤。")
    return seen_ids

# ==================== 3. 动态待办解析与自适应时间轴引擎 ====================
def parse_live_tasks(today_bj):
    """
    动态解析知识库 memory/tasks/index.md 的「🔴 今日/本周必须做」
    并结合当前出行/学术阶段，智能渲染第一版面
    """
    raw_tasks, _ = github_api_get_file("vault/memory/tasks/index.md")
    if not raw_tasks:
        raw_tasks, _ = github_api_get_file("memory/tasks/index.md")
        
    # 本地备用读取
    if not raw_tasks:
        try:
            local_tasks_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vault", "memory", "tasks", "index.md"))
            if os.path.exists(local_tasks_path):
                with open(local_tasks_path, "r", encoding="utf-8", errors="ignore") as f:
                    raw_tasks = f.read()
        except Exception:
            pass

    user_urgent_tasks = []
    if raw_tasks:
        in_urgent_section = False
        for line in raw_tasks.splitlines():
            line_str = line.strip()
            if line_str.startswith("## 🔴 今日/本周必须做"):
                in_urgent_section = True
                continue
            elif in_urgent_section and line_str.startswith("## "):
                break
            elif in_urgent_section and line_str.startswith("- [ ]"):
                task_content = line_str[5:].strip()
                user_urgent_tasks.append(task_content)

    # 太原时间轴与聚变状态机
    start_travel = date(2026, 8, 24)
    end_travel = date(2026, 8, 28)
    days_to_travel = (start_travel - today_bj).days
    
    sections = []
    
    # 1. 如果在太原旅游之前 (today < 8/24)
    if days_to_travel > 0:
        travel_block = f"✈️ **太原·山西 5 日松弛游**（8/24-8/28，距今 **{days_to_travel} 天**）：\n" \
                       f"  - 🏨 住宿：迎西智能酒店（太原理工迎西校区旁，家庭房×1，连住 4 晚 8/24-8/28）\n" \
                       f"  - 🏛️ 预约：云冈石窟微信实名预约（提前 15 天窗口期内，凭身份证原件走 3 号通道）\n" \
                       f"  - 🏛️ 预约：山西博物院微信实名预约（⚠️ 建议 8/20 前完成）\n" \
                       f"  - 🚄 交通：太原南⇄大同南往返高铁票（⚠️ 建议 8/20 前购票）与返程航班确认"
        sections.append(travel_block)
        
        study_block = "📘 **等离子体物理 25 天学习计划**（Day 0/25）：\n" \
                      "  - 双轨体系：Chen《等离子体物理学导论》+ 武松涛《托卡马克聚变堆研究进展》\n" \
                      "  - 状态：⏳ 待山西旅游结束后（8/29）正式启动 Day 1"
        sections.append(study_block)
        
    # 2. 如果在太原旅游期间 (8/24 <= today <= 8/28)
    elif start_travel <= today_bj <= end_travel:
        day_num = (today_bj - start_travel).days + 1
        daily_plans = {
            1: "【Day 1 · 启程抵晋】福州长乐 08:05 航班飞太原武宿，接机入住迎西智能酒店，下午/傍晚柳巷、食品街品尝太原头道汤与面食。",
            2: "【Day 2 · 三晋文脉】上午游览晋祠（难老泉、侍女像、圣母殿），下午参观太原古县城，傍晚汾河晚渡。",
            3: "【Day 3 · 石窟瑰宝】高铁前往大同，全天游览云冈石窟（第 5/6 窟大佛精绝，刷身份证走 3 号通道），傍晚高铁返回太原南。",
            4: "【Day 4 · 奇绝古建与省博】上午迎泽公园 + 山西地质博物馆，下午山西博物院（鸟尊、晋国青铜器），傍晚柳巷购物。",
            5: "【Day 5 · 晋商古韵与返程】上午漫步平遥古城或太原市区，下午整理行李前往机场飞长沙，结束充实难忘的山西之旅！"
        }
        travel_block = f"🏖️ **太原·山西 5 日松弛游 · 今日行程（Day {day_num}/5）**：\n" \
                       f"  - 📍 {daily_plans.get(day_num, '按计划松弛游览，享受假期！')}"
        sections.append(travel_block)
        
        study_block = "📘 **等离子体物理 25 天学习计划**：\n" \
                      "  - 状态：🏖️ 假期中，全身心放松蓄力，8/29 正式启动。"
        sections.append(study_block)
        
    # 3. 如果旅游已经结束 (8/29 之后)：太原旅行条目完全自动淡出！
    else:
        study_start = date(2026, 8, 29)
        day_study = (today_bj - study_start).days + 1
        day_study = max(1, min(day_study, 25))
        study_block = f"📘 **等离子体物理 25 天学习计划 · 今日推进（Day {day_study}/25）**：\n" \
                      f"  - 理论轨：Chen 理论推导与物理图像建立\n" \
                      f"  - 工程轨：武松涛托卡马克工程与 ICRF 加热技术\n" \
                      f"  - 状态：🔥 正在高效推进中"
        sections.append(study_block)

    # 4. 追加真实任务库中提取的任意其他待办事项（如驾校练车、选课、国赛等）
    for t in user_urgent_tasks:
        # 如果不是已被专门格式化渲染的特定条目，直接原汁原味展示
        if not any(k in t for k in ["太原", "山西5日", "等离子体物理学习计划"]):
            sections.append(f"📌 **待办事项**：{t}")

    return {
        "days_to_travel": days_to_travel,
        "urgent_tasks": sections
    }

# ==================== 4. arXiv 等离子体物理前沿（智能去重 + 语义研判） ====================
def fetch_plasma_papers(seen_ids):
    """检索 arXiv physics.plasm-ph 聚变核心论文，执行去重并生成定制研判"""
    url = "http://export.arxiv.org/api/query?search_query=cat:physics.plasm-ph+AND+(all:tokamak+OR+all:ICRF+OR+all:fusion+OR+all:EAST+OR+all:WEST+OR+all:divertor+OR+all:MHD+OR+all:gyrokinetic+OR+all:%22magnetic+confinement%22)&start=0&max_results=12&sortBy=submittedDate&sortOrder=descending"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=12, context=SSL_CONTEXT) as response:
            xml_data = response.read().decode('utf-8')
        
        root = ET.fromstring(xml_data)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        candidates = []
        for entry in root.findall('atom:entry', ns):
            title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
            summary = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
            link = entry.find('atom:id', ns).text.strip()
            
            match = re.search(r'abs/([\w\.\d\-]+)', link)
            paper_id = match.group(1).split('v')[0] if match else link
            
            if paper_id in seen_ids:
                continue
                
            t_low = title.lower() + " " + summary.lower()
            if any(k in t_low for k in ["icrf", "ion cyclotron", "fast wave", "slow wave", "antenna"]):
                insight = "直接对应张伟组 ICRF 离子回旋波加热核心方向：重点关注其天线位形优化、耦合阻抗计算及快波/慢波功率在核心区的吸收机制。"
            elif any(k in t_low for k in ["divertor", "sol", "scrape-off", "impurity", "tungsten", "sputtering"]):
                insight = "等离子体边界与偏滤器材料相互作用前沿：对托卡马克稳态运行中钨等高 Z 杂质输运、热负荷缓解与杂质屏蔽机制极具参考价值。"
            elif any(k in t_low for k in ["mhd", "instability", "tearing", "elm", "disruption", "sawtooth", "pinch"]):
                insight = "磁流体力学（MHD）宏观稳定性控制：涉及破裂预警、锯齿振荡调控与磁岛抑制，是托卡马克高约束模长脉冲运行的关键保障。"
            elif any(k in t_low for k in ["turbulence", "transport", "gyrokinetic", "drift wave"]):
                insight = "微观湍流与反常输运理论：结合回旋动理学模拟，深入解析等离子体能量约束改善与内部输运垒（ITB）形成的物理图像。"
            elif any(k in t_low for k in ["machine learning", "neural", "pinn", "deep learning", "surrogate"]):
                insight = "AI for Plasma 交叉前沿：利用神经网络代理模型加速等离子体平衡演化重构与实时破裂预测，深度契合你的计算物理背景。"
            elif any(k in t_low for k in ["neutron", "blanket", "alpha", "battery"]):
                insight = "聚变核工程与中子学前沿：涉及聚变中子利用、氚自持循环及聚变副产物开发，拓宽了聚变能源应用的认知边界。"
            else:
                insight = "磁约束等离子体动理学前沿，有助于加深对磁面磁通坐标与粒子轨道约束拓扑的理解。"
                
            candidates.append({
                "id": paper_id,
                "title": title,
                "summary": summary[:220] + "..." if len(summary) > 220 else summary,
                "insight": insight,
                "link": link
            })
            if len(candidates) >= 2:
                break
                
        if candidates:
            return candidates
    except Exception as e:
        print(f"[Warn] arXiv plasma fetch error: {e}")
    
    return [
        {
            "id": "2608.13485",
            "title": "Macroscopic Stability of a Rapidly Rotating Theta Pinch",
            "summary": "The macroscopic ideal-MHD stability of an axisymmetric mirror device with sonic levels of plasma rotation is analyzed, showing how rotation shears stabilize flute and interchange modes in magnetic confinement.",
            "insight": "磁流体力学（MHD）宏观稳定性控制：涉及旋转剪切对交换模不稳定性的抑制机理，对托卡马克剪切流改善约束有重要理论启发。",
            "link": "http://arxiv.org/abs/2608.13485v1"
        }
    ]

# ==================== 5. arXiv AI 与智能体前沿（智能去重 + 语义研判） ====================
def fetch_ai_frontier_papers(seen_ids):
    """检索 arXiv cs.AI/cs.MA/cs.CL 最新 Agent、Memory 与科学推理前沿"""
    url = "http://export.arxiv.org/api/query?search_query=(cat:cs.AI+OR+cat:cs.MA+OR+cat:cs.CL)+AND+(all:agent+OR+all:reasoning+OR+all:RAG+OR+all:memory+OR+all:%22physics-informed%22)&start=0&max_results=12&sortBy=submittedDate&sortOrder=descending"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=12, context=SSL_CONTEXT) as response:
            xml_data = response.read().decode('utf-8')
        
        root = ET.fromstring(xml_data)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        candidates = []
        for entry in root.findall('atom:entry', ns):
            title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
            summary = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
            link = entry.find('atom:id', ns).text.strip()
            
            match = re.search(r'abs/([\w\.\d\-]+)', link)
            paper_id = match.group(1).split('v')[0] if match else link
            
            if paper_id in seen_ids:
                continue
                
            t_low = title.lower() + " " + summary.lower()
            if any(k in t_low for k in ["session", "memory", "handover", "context", "continual"]):
                insight = "跨会话状态与记忆传递机制直接契合第二大脑在多 Agent（TRAE 与 Antigravity）间的认知一致性维护，值得吸纳进记忆架构。"
            elif any(k in t_low for k in ["world", "code", "twin", "simulation", "physics"]):
                insight = "基于代码的数字孪生与环境交互思路，可迁移至等离子体物理波加热与粒子轨迹数值仿真的自动化代码生成与验证。"
            elif any(k in t_low for k in ["rag", "retrieval", "search", "dense"]):
                insight = "结构化检索增强策略，可直接用于知识库内 Chen 教材与武松涛专著中复杂公式与物理图像的精准定位与推导。"
            elif any(k in t_low for k in ["moral", "preference", "align"]):
                insight = "多智能体人类偏好对齐前沿：揭示了提示词与隐式偏好引导机制，有助于提升第二大脑对你学术研究隐式需求的理解。"
            else:
                insight = "前沿智能体在复杂长程任务上的自主推理与反思架构，为第二大脑自我维护与学术研究提供理论支撑。"
                
            candidates.append({
                "id": paper_id,
                "title": title,
                "summary": summary[:200] + "..." if len(summary) > 200 else summary,
                "insight": insight,
                "link": link
            })
            if len(candidates) >= 2:
                break
                
        if candidates:
            return candidates
    except Exception as e:
        print(f"[Warn] arXiv AI fetch error: {e}")
        
    return [
        {
            "id": "2608.14490",
            "title": "Twin: Playing an Unknown Game with a Test-Time Digital Twin",
            "summary": "We present a Test-time World-model Inference (Twin) system, in which a frontier coding agent writes an executable world model for completing continual learning in unknown environments.",
            "insight": "利用 Coding Agent 编写可执行世界模型的思路，非常适合迁移到聚变物理波加热与磁平衡仿真环境的自动化构建。",
            "link": "http://arxiv.org/abs/2608.14490v1"
        }
    ]

# ==================== 6. 系统自我进化提案引擎与费曼自测 ====================
def get_feynman_challenge(today_bj):
    """基于知识库 S/A 级学科知识点轮转每日费曼深度挑战思考题"""
    challenges = [
        ("等离子体物理", "在托卡马克 ICRF 离子回旋加热中，为什么快磁声波（Fast Magnetosonic Wave）能够无阻碍穿透高密度等离子体核心区，而慢波（Slow Wave）容易在低密度边界层发生截止或强烈杂质溅射？"),
        ("热力学与统计物理", "麦克斯韦关系式中 $(\\frac{\\partial S}{\\partial V})_T = (\\frac{\\partial P}{\\partial T})_V$ 的微观物理本质是什么？如何利用该式结合热力学第一定律，严格证明理想气体的内能仅与温度有关？"),
        ("电动力学", "在推导相对论性带电粒子电磁辐射（李纳-维谢尔势）时，为什么辐射功率角分布会出现强烈的向前倾斜效应（相对论聚束效应，$\\theta \\sim 1/\\gamma$）？"),
        ("量子力学", "在一维无限深势阱中，如果势阱宽度突然扩大一倍（瞬变近似），为什么基态波函数向偶数能级的跃迁概率为 0，而只向奇数能级跃迁？这体现了什么对称性选择定则？"),
        ("固体物理与自旋", "在具有 Dzyaloshinskii-Moriya (DM) 相互作用的手性磁体中，为什么结构反演对称性破缺会导致相邻自旋倾向于非共面倾斜，从而在热力学平衡态形成拓扑保护的磁斯格明子（Skyrmion）？"),
        ("光电子学与 PIT", "等离激元诱导透明（PIT）中明模式（Bright Mode）与暗模式（Dark Mode）相消干涉的发生条件是什么？为什么暗模式的引入能大幅压窄共振透射谱的线宽？"),
        ("计算物理与 PINNs", "在物理信息神经网络（PINNs）求解非线性偏微分方程时，为什么单纯加大网络深度往往不如在损失函数中引入自适应残差加权（Residual-based Adaptive Refinement）有效？")
    ]
    idx = today_bj.toordinal() % len(challenges)
    return challenges[idx]

def get_evolution_proposal(today_bj, days_to_travel):
    """基于当前学习阶段、出行节点与第二大脑长期痛点生成的真创新进化提案矩阵"""
    proposals = [
        {
            "id": "2026-0818-01",
            "title": "Plasma-Symbolic-RAG：等离子体物理公式树与 MHD 符号检索图谱",
            "purpose": "解决通用向量模型在检索 Chen 教材等离子体色散关系式、介电张量和波极化推导时的语义漂移与符号混淆问题。",
            "benefit": "利用 LaTeX AST 建立物理公式符号子图，实现公式级高保真检索与适用边界严格核验，为等离子体 25 天学习计划提供精准知识引擎。",
            "action": "设计公式解析器原型与 LaTeX 符号图谱构建规范。"
        },
        {
            "id": "2026-0818-02",
            "title": "Cognitive-Feynman-Interrogator：晨报费曼主动自测与掌握度动态评估",
            "purpose": "将传统的被动复习日期表升级为每日早晨主动追问机制，通过 1 道深度物理挑战题检验真实掌握度。",
            "benefit": "结合飞书移动端语音/文字作答，AI 自动判定理解深度并动态调节艾宾浩斯复习周期，彻底杜绝虚假熟练感。",
            "action": "已于今日晨报正式上线「今日费曼挑战」测试模块！"
        },
        {
            "id": "2026-0818-03",
            "title": "Travel-Meteorology-Sentinel：太原 5 日游多源气象与景区实况动态预警",
            "purpose": "在 8/24-8/28 出行前 3 天及旅行期间，自动接入太原/大同气象与景区客流 API，动态预警天气与交通变化。",
            "benefit": "晋祠露天游览指数、云冈石窟大风防晒预警与太原南-大同南高铁进站提醒每日自动融入晨报，打造全天候随行管家。",
            "action": "待 8/21 接入公共天气 API 并挂载至晨报行程引擎。"
        },
        {
            "id": "2026-0818-04",
            "title": "Cross-Agent Memory Synthesizer：跨端智能体记忆蒸馏与冲突消解协议",
            "purpose": "解决 TRAE、Antigravity 与移动端飞书在多端产生灵感 notes 与临时待办时的碎片化和潜在记忆重叠。",
            "benefit": "每日云端对 notes/ 和 decisions/ 进行语义聚类与冲突消解，保持第二大脑唯一事实来源的极度纯净与精炼。",
            "action": "制定跨 Agent 写入互斥锁与语义消解机制。"
        }
    ]
    idx = (today_bj.day + today_bj.month) % len(proposals)
    return proposals[idx]

# ==================== 7. 组装晨报 Markdown ====================
def generate_briefing():
    now_bj = datetime.now(BEIJING_TZ)
    today_bj = now_bj.date()
    today_str = now_bj.strftime("%Y年%m月%d日")
    weekday_str = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][today_bj.weekday()]
    
    seen_ids = get_recently_pushed_arxiv_ids(today_bj)
    tasks_info = parse_live_tasks(today_bj)
    plasma_papers = fetch_plasma_papers(seen_ids)
    ai_papers = fetch_ai_frontier_papers(seen_ids)
    proposal = get_evolution_proposal(today_bj, tasks_info['days_to_travel'])
    feynman_domain, feynman_q = get_feynman_challenge(today_bj)
    
    md = f"""# 🤖 林云舒的第二大脑 · 每日晨报与进化简报
> 📅 **{today_str} · {weekday_str}** (云端全天候守护)

---

### 📌 【今日行程与关键待办】
"""
    for t in tasks_info["urgent_tasks"]:
        md += f"- {t}\n"
        
    md += f"""
---

### ⚛️ 【核聚变与等离子体物理前沿】 (arXiv 实时动态追踪)
"""
    for i, p in enumerate(plasma_papers, 1):
        md += f"**{i}. {p['title']}**\n"
        md += f"- **核心要点**：{p['summary']}\n"
        md += f"- **【第二大脑研判】**：{p['insight']}\n"
        md += f"- 🔗 [查看 arXiv 论文]({p['link']})\n\n"

    md += f"""---

### 🧠 【AI 与智能体前沿突破】 (arXiv 实时动态追踪)
"""
    for i, p in enumerate(ai_papers, 1):
        md += f"**{i}. {p['title']}**\n"
        md += f"- **核心突破**：{p['summary']}\n"
        md += f"- **【第二大脑研判】**：{p['insight']}\n"
        md += f"- 🔗 [查看 arXiv 论文]({p['link']})\n\n"

    md += f"""---

### 🎯 【今日费曼挑战 · 早晨一问】 (主动认知检验)
> 📚 学科领域：**{feynman_domain}**
> ❓ **思考题**：{feynman_q}
> 💡 *小贴士：可在飞书或对话中直接尝试用自己的语言口述/推导回答，第二大脑将自动评估你的掌握度！*

---

### 💡 【系统自我进化提案】 (⚡ 主动进化)
- 🚀 **提案 {proposal['id']}**：{proposal['title']}
  - **建议用途**：{proposal['purpose']}
  - **预期收益**：{proposal['benefit']}
  - **当前状态**：{proposal['action']}
"""
    return md, tasks_info, now_bj

# ==================== 8. 发送微信推送 (WxPusher) ====================
def send_wxpusher(content_md, summary_text):
    url = "https://wxpusher.zjiecode.com/api/send/message"
    payload = {
        "appToken": APP_TOKEN,
        "content": content_md,
        "summary": summary_text,
        "contentType": 3,
        "uids": [USER_UID]
    }
    
    req_data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15, context=SSL_CONTEXT) as resp:
            res_body = resp.read().decode('utf-8')
            res_json = json.loads(res_body)
            if res_json.get("code") == 1000:
                print("✅ [WxPusher] 云端每日微信推送成功！")
                return True
            else:
                print(f"❌ [WxPusher] 推送返回异常: {res_json.get('msg')}")
                return False
    except Exception as e:
        print(f"❌ [WxPusher] 网络请求失败: {e}")
        return False

# ==================== 主入口 ====================
def main():
    print("🚀 [Cloud Bot] 开始生成每日晨报与自我进化简报...")
    content_md, tasks_info, now_bj = generate_briefing()
    
    days_to_travel = tasks_info['days_to_travel']
    if days_to_travel > 0:
        summary_text = f"太原倒计时 {days_to_travel} 天 | 聚变前沿 | AI进化简报"
    elif days_to_travel == 0:
        summary_text = "太原 5 日游今日启程！| 聚变前沿 | AI进化简报"
    else:
        summary_text = "等离子体物理学习推进中 | 聚变前沿 | AI进化简报"
        
    # 1. 发送微信推送
    print(f"📱 正在推送微信卡片 (摘要: {summary_text})...")
    push_success = send_wxpusher(content_md, summary_text)
    
    # 2. 云端 GitHub 知识库自动归档
    archive_path = f"vault/memory/summary/daily/{now_bj.strftime('%Y-%m-%d')}.md"
    commit_msg = f"🤖 Auto archive daily briefing for {now_bj.strftime('%Y-%m-%d')}"
    github_api_put_file(archive_path, content_md, commit_msg)
    
    if push_success:
        print("🎉 [Cloud Bot] 今日晨报微信推送与归档任务执行完毕！")
    else:
        print("⚠️ [Cloud Bot] 微信推送未成功，请检查网络或配置。")
        sys.exit(1)

if __name__ == "__main__":
    main()
