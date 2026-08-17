# 🤖 J.A.R.V.I.S. / 第二大脑 · 云端每日晨报与自我进化守护 Bot

> ☁️ 基于 GitHub Actions 的全天候云端定时推送机器人。  
> ⏰ **每天北京时间 08:00 (UTC 00:00)** 准时自动运行，将最新科研动态与行程推送至手机微信。  
> 🔋 **无需开启电脑，365天全自动执行。**

---

## 📌 功能一览
1. **行程与任务倒计时**：自动同步太原 5 日游、等离子体物理 25 天学习计划倒计时与预约待办；
2. **核聚变前沿监控**：实时调用 arXiv API，追踪 `physics.plasm-ph` 最新 ICRF / EAST / 托卡马克论文；
3. **AI 突破与第二大脑研判**：动态捕捉大模型与语音智能体突破，给出专属分析；
4. **系统自我进化提案**：主动提炼可用于优化个人知识库或工具链的技术。

---

## 🚀 部署步骤 (1分钟完成)

### 1. 新建 GitHub 私有仓库
1. 打开 [GitHub](https://github.com/new)，新建一个仓库，名字叫：`jarvis-daily-bot`
2. 选择 **Private（私有仓库）**

### 2. 推送本文件夹代码到 GitHub
在当前目录运行终端命令：
```bash
git init
git add .
git commit -m "feat: init jarvis cloud daily bot"
git branch -M main
git remote add origin https://github.com/althouseaikman684-stack/jarvis-daily-bot.git
git push -u origin main
```

### 3. 配置 GitHub Secrets (安全存储 Key，避免代码泄露)
在 GitHub 仓库页面：
1. 点击 **Settings** $\to$ **Secrets and variables** $\to$ **Actions**
2. 点击 **New repository secret**，添加以下两项：
   - `WXPUSHER_APP_TOKEN` : `AT_MERfNtorNArt4Alo9AkpUx1GRjpieamX`
   - `WXPUSHER_UID` : `UID_HtpiaxeUlxUPMe6lwisMaavhlC0u`

---

## 🧪 手动测试
进入 GitHub 仓库的 **Actions** 标签页，点击左侧 **Second Brain Daily Morning Briefing**，再点击右侧 **Run workflow**，即可立即触发一次云端推送测试！
