# Yuxi 知识库与知识图谱架构梳理

## 一、整体架构关系

```
知识库 (Knowledge Base)
├── 知识库管理器 (KnowledgeBaseManager)
│   ├── MilvusKB     — 纯向量检索知识库 (Milvus)
│   ├── LightRagKB   — 图+向量双重知识库 (LightRAG + Neo4j + Milvus)
│   └── DifyKB       — 只读检索知识库 (Dify)
│
├── 图谱服务 (Graph)
│   ├── UploadGraphService    — Neo4j 直连的上传图谱 (三元组管理)
│   └── GraphAdapterFactory   — 统一适配器工厂
│       ├── LightRAGGraphAdapter  — 从 LightRAG 的 Neo4j 子图查询
│       └── UploadGraphAdapter    — 从 Upload 图谱查询 (支持向量相似度)
│
└── 周边模块
    ├── RAG 评估 (Evaluation)     — 基准管理 → 评估执行 → 指标计算
    └── 思维导图 (MindMap)        — AI 根据知识库文件生成导图
```

**核心要点**：知识库是容器，图谱是知识库的一种数据表现形式（尤其是 `lightrag` 类型）。两者通过 `GraphAdapterFactory` 实现统一查询入口。

---

## 二、知识库模块 (Knowledge Base)

### 2.1 数据模型（PostgreSQL）

```python
# backend/package/yuxi/storage/postgres/models_knowledge.py

KnowledgeBase 表:
  db_id, name, description, kb_type, embed_info, llm_info,
  query_params, additional_params, share_config, mindmap, sample_questions

KnowledgeFile 表:
  file_id, db_id, parent_id, filename, original_filename, file_type,
  path, minio_url, markdown_file, status, content_hash,
  processing_params, is_folder
```

文件状态流转：

```
UPLOADED → PARSING → PARSED → INDEXING → INDEXED
                ↓                    ↓
          ERROR_PARSING        ERROR_INDEXING
```

### 2.2 三种知识库实现

| 类型 | 实现类 | 存储后端 | 独特能力 |
|------|--------|----------|----------|
| `milvus` | **MilvusKB** | Milvus 向量库 | 标准 RAG 检索，无图谱 |
| `lightrag` | **LightRagKB** | Milvus + Neo4j | 同时构建向量索引和图谱（实体+关系），删除时需清理两个后端 |
| `dify` | **DifyKB** | Dify Dataset | 只读检索，不做写入 |

### 2.3 工厂注册

```python
# backend/package/yuxi/knowledge/factory.py
KnowledgeBaseFactory:
  register(kb_type, kb_class, default_config)  # 注册新类型
  create(kb_type, work_dir, **kwargs)           # 创建实例
  get_available_types()                          # 获取所有类型
```

已注册：`milvus`、`lightrag`、`dify`

### 2.4 文档处理全链路

```
上传文件 (MinIO)
  → 分块 (chunking/ragflow_like/, 支持 markdown/qa/laws/book 等解析器)
  → Embedding (通过配置的 embedding 模型)
  → 入库 (Milvus vector insert)
  → (LightRAG 额外步骤) 实体抽取 → Neo4j 图谱构建
```

### 2.5 知识库管理器

```python
# backend/package/yuxi/knowledge/manager.py
KnowledgeBaseManager:
  _get_or_create_kb_instance(kb_type)     # 按类型获取/创建 KB 实例
  _get_kb_for_database(db_id)             # 根据 db_id 获取对应 KB
  create_database() / delete_database()   # CRUD
  add_file_record() / parse_file() / index_file()  # 文件处理
  query_database() / query_test()         # 查询
```

---

## 三、知识图谱模块 (Knowledge Graph)

### 3.1 图谱的双轨制

Yuxi 实际上有**两套图谱系统**，通过 `GraphAdapterFactory` 抽象为统一接口：

```
图谱来源:
  ├── LightRAG 自动构建
  │   └── 创建 lightrag 知识库时自动生成
  │       写入 Neo4j, 图标签: kb_{db_id}
  │
  └── 手动上传
      └── JSONL 三元组文件, 通过 UploadGraphService 写入 Neo4j
```

### 3.2 图谱适配器系统

```python
# backend/package/yuxi/knowledge/graphs/adapters/

GraphAdapter (ABC)                       # 抽象基类
  ├── query_nodes(config)                # 统一查询接口
  ├── normalize_node() / normalize_edge()  # 标准化
  ├── get_labels()                       # 标签统计
  └── get_stats()                        # 节点/边统计

BaseNeo4jAdapter                         # 公共 Neo4j 查询基类

LightRAGGraphAdapter(BaseNeo4jAdapter)   # LightRAG 图谱适配器
  └── 通过 Neo4j 查询 kb_{db_id} 标签节点

UploadGraphAdapter(BaseNeo4jAdapter)     # Upload 图谱适配器
  └── 支持 embedding 向量相似度查询和阈值查询

GraphAdapterFactory:
  detect_graph_type(db_id)               # 自动检测图谱类型
  create_adapter_by_db_id(db_id)         # 创建对应适配器
```

### 3.3 统一图谱查询架构

```
前端 API 调用
  ↓
graph_router.py → _get_graph_adapter(db_id)
  ↓
GraphAdapterFactory.create_adapter_by_db_id(db_id)
  ↓ (自动检测图谱类型)
  ├── LightRAGGraphAdapter    (如果 db_id 对应 lightrag 知识库)
  └── UploadGraphAdapter      (如果 db_id 对应 upload 图谱)
  ↓
统一返回: nodes[], edges[]  (前端无需区分类型)
```

### 3.4 图谱 API 总览

| 端点 | HTTP方法 | 用途 |
|------|---------|------|
| `/api/graph/list` | GET | 列出所有图谱（合并 Neo4j + LightRAG 中的图谱） |
| `/api/graph/subgraph` | GET | 统一子图查询（keyword/threshold/limit） |
| `/api/graph/labels` | GET | 标签统计 |
| `/api/graph/stats` | GET | 节点/边统计信息 |
| `/api/graph/neo4j/info` | GET | Neo4j 数据库连接信息 |
| `/api/graph/neo4j/index-entities` | POST | 为实体建立向量索引（支持语义搜索） |
| `/api/graph/neo4j/add-entities` | POST | 通过 JSONL 批量导入三元组 |

### 3.5 上传图谱服务

```python
# backend/package/yuxi/knowledge/graphs/upload_graph_service.py
UploadGraphService:
  is_running()              # 检查 Neo4j 是否运行
  get_graph_info()          # 获取图谱信息
  jsonl_file_add_entity()   # 从 JSONL 文件添加实体三元组
  query_node()              # 按关键词/阈值查询节点
  add_embedding_to_nodes()  # 为节点添加嵌入向量
```

---

## 四、知识库 API 总览

### 4.1 知识库管理

| 端点 | HTTP方法 | 用途 |
|------|---------|------|
| `/api/knowledge/databases` | GET | 获取所有知识库 |
| `/api/knowledge/databases` | POST | 创建知识库 |
| `/api/knowledge/databases/accessible` | GET | 获取可访问知识库（非管理员） |
| `/api/knowledge/databases/{db_id}` | GET/PUT/DELETE | 知识库 CRUD |
| `/api/knowledge/types` | GET | 获取支持的知识库类型 |
| `/api/knowledge/stats` | GET | 知识库统计信息 |
| `/api/knowledge/generate-description` | POST | AI 生成知识库描述 |

### 4.2 文档管理

| 端点 | HTTP方法 | 用途 |
|------|---------|------|
| `/api/knowledge/databases/{db_id}/documents` | POST | 添加文档（上传+解析+入库） |
| `/api/knowledge/databases/{db_id}/documents/parse` | POST | 手动解析文档 |
| `/api/knowledge/databases/{db_id}/documents/index` | POST | 手动入库文档 |
| `/api/knowledge/databases/{db_id}/documents/{doc_id}` | GET/DELETE | 获取/删除文档 |
| `/api/knowledge/databases/{db_id}/documents/batch` | DELETE | 批量删除文档 |
| `/api/knowledge/databases/{db_id}/documents/{doc_id}/download` | GET | 下载原始文件 |
| `/api/knowledge/databases/{db_id}/folders` | POST | 创建文件夹 |
| `/api/knowledge/databases/{db_id}/documents/{doc_id}/move` | PUT | 移动文档 |

### 4.3 检索查询

| 端点 | HTTP方法 | 用途 |
|------|---------|------|
| `/api/knowledge/databases/{db_id}/query` | POST | 知识库检索查询 |
| `/api/knowledge/databases/{db_id}/query-test` | POST | 测试查询 |
| `/api/knowledge/databases/{db_id}/query-params` | GET/PUT | 查询参数管理 |
| `/api/knowledge/databases/{db_id}/sample-questions` | GET/POST | 示例问题管理 |

### 4.4 文件操作

| 端点 | HTTP方法 | 用途 |
|------|---------|------|
| `/api/knowledge/files/fetch-url` | POST | 抓取 URL 内容 |
| `/api/knowledge/files/upload` | POST | 上传文件 |
| `/api/knowledge/files/supported-types` | GET | 获取支持的文件类型 |
| `/api/knowledge/files/markdown` | POST | 保存 Markdown 内容 |

---

## 五、RAG 评估体系

### 5.1 核心模块

```python
# backend/package/yuxi/knowledge/eval/

evaluator.py              # evaluate_question() 单条评估
metrics.py                 # RetrievalMetrics + AnswerMetrics (LLM Judge)
benchmark_generation.py    # 自动从知识库文件生成评估基准
```

### 5.2 数据模型

```python
EvaluationBenchmark:         # 评估基准（问题集 + 黄金答案 + 黄金 Chunk）
  benchmark_id, db_id, name, description, question_count,
  has_gold_chunks, has_gold_answers

EvaluationResult:            # 一次评估任务
  task_id, db_id, benchmark_id, status, retrieval_config,
  metrics, overall_score

EvaluationResultDetail:      # 每条问题详细结果
  task_id, query_index, query_text, gold_chunk_ids, gold_answer,
  generated_answer, retrieved_chunks, metrics
```

### 5.3 评估 API

| 端点 | HTTP方法 | 用途 |
|------|---------|------|
| `/api/evaluation/databases/{db_id}/benchmarks/upload` | POST | 上传评估基准 |
| `/api/evaluation/databases/{db_id}/benchmarks/generate` | POST | 自动生成评估基准 |
| `/api/evaluation/databases/{db_id}/benchmarks` | GET | 获取基准列表 |
| `/api/evaluation/databases/{db_id}/benchmarks/{benchmark_id}` | GET/DELETE | 基准详情/删除 |
| `/api/evaluation/benchmarks/{benchmark_id}/download` | GET | 下载基准文件 |
| `/api/evaluation/databases/{db_id}/run` | POST | 运行 RAG 评估 |
| `/api/evaluation/databases/{db_id}/results/{task_id}` | GET/DELETE | 评估结果管理 |
| `/api/evaluation/databases/{db_id}/history` | GET | 评估历史 |

---

## 六、思维导图模块

| 端点 | HTTP方法 | 用途 |
|------|---------|------|
| `/api/mindmap/databases/{db_id}/files` | GET | 获取知识库文件列表 |
| `/api/mindmap/generate` | POST | AI 生成思维导图 |
| `/api/mindmap/databases` | GET | 获取知识库概览 |
| `/api/mindmap/database/{db_id}` | GET | 获取已保存的思维导图 |

### 核心工具

```python
# backend/package/yuxi/knowledge/utils/mindmap_utils.py
MINDMAP_SYSTEM_PROMPT         # AI 生成思维导图的系统提示词
build_database_file_list()     # 构建文件列表
collect_mindmap_files()        # 收集导图相关文件
build_mindmap_user_message()   # 构建用户消息
parse_mindmap_content()        # 解析生成的内容
```

---

## 七、Agent 集成

### 7.1 中间件注入（工具层）

```python
# backend/package/yuxi/agents/middlewares/knowledge_base_middleware.py
KnowledgeBaseMiddleware:
  注入 3 个通用工具:
    - list_kbs       # 列出用户可访问的知识库
    - get_mindmap    # 获取知识库思维导图
    - query_kb       # 在指定知识库中检索
```

### 7.2 文件系统挂载（后端层）

```python
# backend/package/yuxi/agents/backends/knowledge_base_backend.py
KnowledgeBaseBackend:
  - 将知识库文件挂载为虚拟路径 /home/gem/kbs/
  - resolve_visible_knowledge_bases_for_context()  # 解析上下文中的可见知识库
  - build_visible_knowledge_mounts()               # 构建挂载列表
```

---

## 八、分块策略

```python
# backend/package/yuxi/knowledge/chunking/ragflow_like/

dispatcher.py    # chunk_markdown() 分块调度
presets.py       # 预设配置管理
parsers/         # 多种解析器:
  ├── general.py      # 通用解析
  ├── qa.py           # 问答解析
  ├── laws.py         # 法律文档解析
  ├── book.py         # 书籍解析
  ├── semantic.py     # 语义解析
  └── separator.py    # 分隔符解析
```

---

## 九、前端组件关系

### 9.1 知识库前端

```
DataBaseView.vue (列表页)
  → 创建知识库 → KnowledgeBaseCard 卡片展示
  → 进入详情 → DataBaseInfoView.vue
      ├── FileTable.vue + FileUploadModal.vue — 文件管理
      ├── QuerySection.vue — 检索测试
      ├── MindMapSection.vue — 思维导图
      ├── KnowledgeGraphSection.vue — 图谱可视化 (嵌入)
      └── RAGEvaluationTab.vue + EvaluationBenchmarks.vue — RAG 评估
```

### 9.2 图谱前端

```
GraphView.vue (独立图谱页)
  → 图谱选择器 (按 db_id)
  → GraphCanvas.vue (基于 @antv/g6 渲染)
      ├── 节点点击 → GraphDetailPanel.vue (节点/边详情)
      └── 搜索/缩略图/导出
  → 实体上传 (JSONL 文件)

KnowledgeGraphTool.vue — Agent 工具调用结果的图谱可视化
```

### 9.3 状态管理

| Store | 文件 | 用途 |
|-------|------|------|
| `useDatabaseStore` | `stores/database.js` | 知识库列表、当前知识库、文件管理、查询参数 |
| `useGraphStore` | `stores/graphStore.js` | 图谱数据（使用 `graphology.DirectedGraph`）、选中节点/边 |
| `useGraph` | `composables/useGraph.js` | 图谱交互逻辑（点击、刷新等） |

### 9.4 API 调用层

| 模块 | 文件 | 包含方法 |
|------|------|---------|
| `databaseApi` | `apis/knowledge_api.js` | 知识库 CRUD |
| `documentApi` | `apis/knowledge_api.js` | 文档管理（上传/删除/移动） |
| `queryApi` | `apis/knowledge_api.js` | 检索查询 |
| `fileApi` | `apis/knowledge_api.js` | 文件上传/下载 |
| `typeApi` | `apis/knowledge_api.js` | 类型与统计 |
| `embeddingApi` | `apis/knowledge_api.js` | Embedding 模型状态 |
| `evaluationApi` | `apis/knowledge_api.js` | RAG 评估 |
| `unifiedApi` | `apis/graph_api.js` | 图谱统一查询 |
| `neo4jApi` | `apis/graph_api.js` | Neo4j 直接操作 |

---

## 十、Repository 层

```python
# backend/package/yuxi/repositories/

KnowledgeBaseRepository:
  get_all(), get_by_id(), create(), update(), delete()
  get_accessible_kbs_for_user()

KnowledgeFileRepository:
  get_all(), get_by_file_id(), list_by_db_id()
  upsert(), delete(), delete_by_db_id()
```

---

## 十一、两种核心数据流总结

### 路径 1: 纯知识库 (milvus)

```
文件 → 分块 → Embedding → Milvus → 向量检索 → 回答
```

### 路径 2: 知识库+图谱 (lightrag)

```
文件 → 分块
         ├── Embedding → Milvus (向量索引)
         └── 实体/关系抽取 → Neo4j (图谱索引)

查询时:
  → 向量检索 (Milvus) + 图谱检索 (Neo4j via LightRAG)
  → 融合结果 → 回答
```

两者共享同一套文件管理、查询参数、评估体系，差异仅在于 `kb_type` 决定的底层存储和检索策略。图谱模块通过适配器模式解耦，使前端可以无感切换不同图谱来源。