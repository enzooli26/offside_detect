# V002 来源、阅读范围与检索记录

日期：2026-11-13（北京时间）。配套正文：[固定机位技术调研](01_fixed_camera_offside_technical_survey.md)。

本表提供可追溯来源与本次实际阅读范围；“摘要”不代表阅读全文，“章节”不代表复现。arXiv 收录本身不证明同行评审状态；本文不额外推定发表场所。论文年份按首次提交年，链接固定到本次核验的版本。

## 一、规则、工程文档与实际系统

| ID | 来源与链接 | 本次访问/阅读 | 用途与限制 |
|---|---|---|---|
| S01 | IFAB, [Law 11 — Offside](https://www.theifab.com/laws/latest/offside/) | HTTP 200；阅读越位位置、犯规、例外、接触时刻脚注及相关解释 | 规则主来源；latest 为动态页面，实施须锁定赛事规则版本；未保存官方全文快照 |
| S02 | Genius Sports, George Smith, 2026-10-30, [AFA partnership / SAOT](https://www.geniussports.com/newsroom/genius-sports-expands-afa-partnership-to-bring-faster-offside-decisions-to-argentine-football-with-semi-automated-offside-technology/) | HTTP 200；阅读公告正文 | 相机跟踪、AI、触球时刻、VAR 和三维呈现；供应商自述，含未来部署计划，不是独立评测 |
| S03 | SoccerNet, [Camera Calibration task](https://www.soccer-net.org/tasks/camera-calibration) | HTTP 200；数据规模与评估说明 | 模块数据，不是端到端越位数据集 |
| S04 | SoccerNet, [Game State Reconstruction task](https://www.soccer-net.org/tasks/game-state-reconstruction) | HTTP 200；任务、标签、公开划分与指标 | 当前页面 57/59/50 与论文总规模应区分；页面另有未填完的挑战数量占位符，不据此推断 |
| S05 | SoccerNet, [sn-gamestate](https://github.com/SoccerNet/sn-gamestate) | HTTP 200；当前 README、组件说明、数据 v1.3 提示、仓库许可证标识 | 当前代码描述不等于 2024 原论文配置；未安装运行；仓库显示 GPL-3.0 |
| S06 | OpenCV, [Homography tutorial](https://docs.opencv.org/4.13.0/d9/dab/tutorial_homography.html) | 4.x 地址重定向至 4.13.0，HTTP 200；平面映射与相机模型说明 | 支持平面几何前提，不能证明项目实际标定精度 |
| S07 | Ultralytics, [Models documentation](https://docs.ultralytics.com/models/) | HTTP 200；模型家族及 Featured Models 说明 | 页面列 YOLO26 和 YOLO11；未下载权重、未比较项目性能；动态文档 |

## 二、论文证据矩阵

| ID | 论文与核验版本 | 阅读范围 | 方法/相关结论 | 本项目采用时的边界 |
|---|---|---|---|---|
| P01 | S. Desai (2025), [Real Time Offside Detection using a Single Camera in Soccer](https://arxiv.org/abs/2502.16030v1) | 摘要；关键点、结果、讨论、未来工作与结论相关正文 | KeypointRCNN、消失点划线；后续工作包含球队识别及攻防标注 | 守门员规则简化不适用于完整 Law 11；演示不等于通用判罚验证 |
| P02 | K. Muthuraman, P. Joshi, S. K. Raman (2018), [Vision Based Dynamic Offside Line Marker for Soccer Games](https://arxiv.org/abs/1804.06438v1) | 摘要 | Hough、颜色量化、连通分量、消失点、KLT | 传统方法背景；未读取实验细节，不给出量化性能判断 |
| P03 | M. Gutiérrez-Pérez, A. Agudo (2024 首次提交), [PnLCalib: Sports Field Registration via Points and Lines Optimization](https://arxiv.org/abs/2404.08401v5) | 摘要；Camera Projection Model、Camera Parameters Estimation、Homography Estimation、Point and Line Refinement 相关正文 | 点线联合标定、重投影优化；地面 H 基于 z=0 | v5 与初次提交年份区分；简化内参/畸变假设需针对固定镜头核查 |
| P04 | N. S. Falaleev, R. Chen (2024), [Enhancing Soccer Camera Calibration Through Keypoint Exploitation](https://arxiv.org/abs/2410.07401v1) | 摘要 | 线与线/圆锥曲线交点、检测与拟合 | 自动标定候选；挑战成绩为作者报告，未复现 |
| P05 | F. Magera, T. Hoyoux, O. Barnich, M. Van Droogenbroeck (2024), [BroadTrack: Broadcast Camera Tracking for Soccer](https://arxiv.org/abs/2412.01721v1) | 摘要 | 转播相机云台/运动时序模型 | 仅在画面几何变化时重点考虑；不是球员 MOT |
| P06 | Y. Zhang et al. (2021 首次提交), [ByteTrack: Multi-Object Tracking by Associating Every Detection Box](https://arxiv.org/abs/2110.06864v3) | 摘要 | 关联高低置信度检测 | 通用跟踪基线；MOT17 成绩不能迁移为越位成绩 |
| P07 | N. Aharon, R. Orfaig, B.-Z. Bobrovsky (2022), [BoT-SORT: Robust Associations Multi-Pedestrian Tracking](https://arxiv.org/abs/2206.14651v2) | 摘要 | 运动、外观、相机运动补偿 | 足球同队外观相似的适配效果待测 |
| P08 | A. Cioppa et al. (2022), [SoccerNet-Tracking: Multiple Object Tracking Dataset and Benchmark in Soccer Videos](https://arxiv.org/abs/2204.06918v2) | 摘要 | 200 段 30 秒及半场跟踪数据 | 跟踪标签不等于越位事件与身体真值 |
| P09 | V. Somers et al. (2024), [SoccerNet Game State Reconstruction: End-to-End Athlete Tracking and Identification on a Minimap](https://arxiv.org/abs/2404.11335v1) | 摘要；另读 S04/S05 | 球员身份、角色、球队、世界位置，GS-HOTA；论文描述 200 段序列 | 原论文与当前仓库、当前公开数据规模分开记录 |
| P10 | V. Golovkin et al. (2025), [From Broadcast to Minimap: Achieving State-of-the-Art SoccerNet Game State Reconstruction](https://arxiv.org/abs/2504.06357v1) | 摘要 | YOLOv5m、SegFormer、增强 DeepSORT、身份信息 | 成绩为作者报告；不是越位专用基准 |
| P11 | G. Van Zandycke, C. De Vleeschouwer (2022), [Ball 3D Localization From A Single Calibrated Image](https://arxiv.org/abs/2204.00003v3) | 摘要；Discussion、Conclusion 正文 | 已知球径与标定；Discussion 报告有利条件下 1.6px 球径 MAE 对应 1.8m 投影误差 | 只对应论文设置，非单目普遍极限，也不能与人体 MPJPE 直接比较 |
| P12 | S. Khan, L. Gajny, J. Lecompte, S. Laporte (2026), [Field Converter: Geometry-Initialized Temporal Residual Refinement for World-Grounded Player Pose Estimation from Soccer Broadcasts](https://arxiv.org/abs/2609.10498v1) | 摘要、引言和相关工作开头；未读完整实验 | 几何初始化、时序残差；摘要给世界坐标误差并指出空中运动限制 | 新近研究候选，所有数字归于作者摘要；端点误差和本项目效果未验证 |
| P13 | P. Rawat (2026), [SMART: SMPLest-X Mesh Adaptation and RAFT Tracking for Soccer Pose Estimation](https://arxiv.org/abs/2605.31551v1) | 摘要 | 人体模型适配、光流、脚部锚定；局部与全局误差明显不同 | FIFA Skeletal Tracking Challenge 设置；未核查完整实验 |
| P14 | A. Cioppa et al. (2026), [SoccerNet 2026 Challenges Results](https://arxiv.org/abs/2607.07320v1) | 摘要 | 包含静态相机世界定位 Synloc、球员中心球动作等任务 | 提供新数据方向；未核查 Synloc 数据下载、许可或完整协议 |

## 三、检索过程

使用已安装的 arXiv MCP Server 0.8.2，先检索与摘要筛选，再对直接越位、几何和单目误差等关键内容做有界正文阅读。检索截止日期设为 2026-11-13；同日排序及搜索结果会随服务索引变化，不承诺重跑时顺序一致。

| 检索式 | 范围与筛选记录 |
|---|---|
| `(ti:offside OR abs:"offside detection") AND (abs:soccer OR abs:football)` | 返回 5 条；排除 2510.22535 的 OFFSIDE 多模态遗忘研究，因与足球规则检测无关 |
| `ti:offside OR (abs:"offside detection" AND (abs:football OR abs:soccer))` | 按日期排序，返回同组 5 条；不据此断言所有越位文献仅有这些 |
| `ti:"SoccerNet" AND (all:tracking OR all:calibration OR all:"game state")` | 服务显示总计 13 条，取前 10 条进行相关性筛选 |
| `ti:"ByteTrack" OR ti:"BoT-SORT" OR ti:"BroadTrack" OR ti:"PnLCalib"` | 总计 10 条，取前 8 条；排除蜜蜂、无人机等无关应用 |
| `(ti:soccer OR ti:football) AND (ti:"ball" OR ti:"pose" OR ti:calibration OR ti:offside)` | 按日期排序，总计 49 条，取前 10 条；补充 Field Converter、SMART 等 2026 研究 |
| `(ti:"SoccerNet" AND (all:"ball action" OR all:"fine-grained")) OR ti:"SoccerTrack"` | 总计 10 条，取前 5 条；补充 2026 挑战总结与动作识别方向 |

上述条数可能跨查询重复，不是唯一文献数量，不构成 PRISMA 流程。另有一次排序值 `submittedDate` 被工具校验拒绝，已改用合法值 `date`；该错误请求不计为成功检索。

正文读取采用下载后的有界片段：P01 约字符 11,950–19,550；P03 约 35,919–47,219；P11 约 31,801–33,701；P12 开头约 12,000 字符。偏移仅作本次工具缓存定位说明，不能作为未来不同格式的固定页码。正文证据应按章节名称和论文版本复核。

## 四、失败访问和覆盖限制

- FIFA 官方 SAOT 技术页面与相关 FIFA 域名路径：返回 HTTP 403；没有将其规格当成本次已核验事实。
- 英超若干推测的历史新闻 ID：404；新闻首页可访问，但未获取可核验 SAOT 正文，因此未作为主来源。
- Genius Sports 的推测 sitemap 和 WordPress 搜索路径：404；最终采用可访问的正式 AFA 公告。
- Google 请求失败、DuckDuckGo 超时、Bing 结果与关键词不相关；未采用这些结果支持结论。
- 没有覆盖所有商业系统、期刊数据库、非 arXiv 会议论文或专利；也未验证任何产品的独立判罚精度。FIFA/英超原始材料可在后续访问条件改善时补充。

## 五、可重复性与后续更新

本版仅保存研究综合与来源元数据，不上传论文全文、数据集、模型权重或原始录像。网页是动态来源，未作完整归档；正式实现前应对规则版本、代码提交、模型权重哈希、数据集版本和许可证建立锁定记录。

未来若更新来源、纠正规则解释或完成视频实验，应新建完成版本，保留本版 Git 历史，并在工作日志中注明改变了哪些结论。报告中的设计建议和算术示例不可被当作实验结果引用。
