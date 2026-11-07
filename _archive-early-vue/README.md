# 归档：早期 Vue 3 版（已废弃）

> 这个目录**不是** Streamlit 旧版的一部分，也**不是**现在线上跑的 Vue 版。
> 它只是 2026-11 把项目从 Streamlit 迁移到 Vue 3 时的第一版试验代码，
> 后来被重构为独立项目（`main` 分支），这里保留仅作历史记录。

## 里面是什么

| 目录 | 内容 | 说明 |
|---|---|---|
| `web/` | 早期的 Vue 3 源码 | 75 景点 / 51 路线 / 11 城市，仅 4 个页面（首页、景点、路线、热度），无登录、无社区 |
| `docs/` | 上面那份源码的构建产物 | 当年靠 GitHub Pages 的 `/docs` 目录部署，现已被 `gh-pages` 分支取代 |

## 和现在的关系

| 版本 | 位置 | 状态 |
|---|---|---|
| **Streamlit 旧版**（155 景点 / 34 路线） | 本分支**根目录**（`Home.py`、`views/`、`data/`） | 线上运行中：<https://south-china-hiking-map.streamlit.app> |
| **早期 Vue 3 版**（75 景点 / 51 路线） | 本目录 | **已废弃**，不部署、不维护 |
| **现在的 Vue 3 完整版**（76 景点 / 53 路线） | `main` 分支（源码）+ `gh-pages` 分支（产物） | 线上运行中：<https://south-china-hiking.app.workbuddy.host/?sharecode=NXC6GS3IF3> |

## 为什么还留着而不是删掉

- 里面有几个数据文件（`web/src/data/spots.js` 等）记录了最早一版景点整理的过程，可能有参考价值
- 删除后 Git 历史虽然还在，但翻起来麻烦

确认不需要了，可以让维护者删掉 entire `_archive-early-vue/` 目录，**不影响任何线上服务**。

---

*归档时间：2026-11-07 · 移动操作仅在本 `master` 分支执行，`main` 与 `gh-pages` 未受影响。*
