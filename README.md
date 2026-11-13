# offside_detect

面向固定机位球场视频的足球越位辅助检测项目。当前完成技术调研，业务原型与视频实验尚未开始。

## 技术调研

- [V002：固定机位足球视频越位检测技术分析](docs/research/01_fixed_camera_offside_technical_survey.md)：规则、已有技术、推荐架构、精度边界和验证计划。
- [V002：来源与检索记录](docs/research/02_sources_and_search_log.md)：论文版本、实际阅读范围、来源限制与检索过程。

初步路线：固定相机标定、球员检测跟踪、人工确认触球时刻、地面位置候选提示与人工复核。地面近似不等于完整身体位置判断，最终是否构成越位犯规还需规则语义确认。

## 工作记录与版本

- [工作日志](WORK_LOG.md)：目标、关键决策、变更、验证与后续事项。
- [协作约定](AGENTS.md)：完成版本的记录、提交和 GitHub 同步要求。
- 每个完成版本通过独立 Git 提交保存，可在 [GitHub 提交历史](https://github.com/enzooli26/offside_detect/commits/main/) 查看、比较或恢复。

当前文档版本：V002（2026-11-13）；协作约定初始版本：V001。
