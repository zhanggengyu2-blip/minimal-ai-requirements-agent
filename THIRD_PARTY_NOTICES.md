# 第三方来源与改造说明

Coo 知识库基于 [AI 电商智能客服](https://github.com/zhanggengyu2-blip/ai-ecommerce-customer-service) 当前 foundation 实现改造，参考 knowledge.py、retrieval.py、providers.py、model_runtime.py、workers.py、ai_api.py、models/knowledge.py、LiveKnowledge.vue 及其发布/权限测试思路。对应文件 SHA 见 docs/v4/IMPLEMENTATION.md。

复用内容包括文本重叠切分、版本成功后生效、有效期选择、向量有效性检查、中文词法/余弦相似度双路召回与 RRF 融合、重排结果校验和来源白名单。适配为本项目的字符串 ID、SQLAlchemy 2、企业/项目/部门权限、环境变量模型配置、现有 API 响应和 Vue UI。没有迁移旧 api/v1 的 OpenSearch、Celery、Redis。

客服工程的上游为 [AgentServe](https://gitee.com/usefullc/agent-serve)，来源提交 781975f7ca6cfff9ba6afefcd669f47a0fdd7f28，采用 Apache License 2.0。原始许可全文保留于 licenses/AgentServe-Apache-2.0.txt。上述复用部分及上游原始代码不宣称为本项目原创。参考项目的来源说明：https://github.com/zhanggengyu2-blip/ai-ecommerce-customer-service/blob/main/THIRD_PARTY_NOTICES.md 。

本次新增主要是企业权限适配、Coo 业务工具与确认机制、私人会话、业务事件和主项目增量集成。各第三方依赖适用各自许可证。
