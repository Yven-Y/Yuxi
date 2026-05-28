# 知识库 & 知识图谱 API 文档

> 所有端点均挂载在 `/api` 前缀下，共 **57 个端点**，分布在 **5 个路由模块**中。
> 非特殊说明，所有端点均需管理员权限（`get_admin_user` 依赖注入）。

---

## 目录

- [一、知识库路由 (`/api/knowledge`)](#一知识库路由-apiknowledge)
  - [1.1 知识库管理](#11-知识库管理)
  - [1.2 文档管理](#12-文档管理)
  - [1.3 知识库查询](#13-知识库查询)
  - [1.4 AI 示例问题](#14-ai-示例问题)
  - [1.5 文件管理](#15-文件管理)
  - [1.6 类型与统计](#16-类型与统计)
  - [1.7 Embedding 模型状态](#17-embedding-模型状态)
  - [1.8 AI 辅助](#18-ai-辅助)
- [二、知识图谱路由 (`/api/graph`)](#二知识图谱路由-apigraph)
- [三、知识库评估路由 (`/api/evaluation`)](#三知识库评估路由-apievaluation)
- [四、思维导图路由 (`/api/mindmap`)](#四思维导图路由-apimindmap)
- [五、仪表盘统计 (`/api/dashboard`)](#五仪表盘统计-apidashboard)

---

## 一、知识库路由 (`/api/knowledge`)

Router 前缀: `/knowledge`

### 1.1 知识库管理

#### `GET /api/knowledge/databases`

获取当前管理员用户有权访问的所有知识库列表。

**响应：** `knowledge_base.get_databases_by_user_id()` 的返回值（包含 `databases` 列表）。

---

#### `POST /api/knowledge/databases`

创建新知识库。

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `database_name` | `str` | 是 | 知识库名称 |
| `description` | `str` | 是 | 知识库描述 |
| `embed_model_name` | `str \| None` | 否 | Embedding 模型名称（非 Dify 类型时必填） |
| `kb_type` | `str` | 否 | 类型，默认 `"lightrag"`（可选: `lightrag`, `milvus`, `dify` 等） |
| `additional_params` | `dict` | 否 | 额外参数，Dify 类型需含 `dify_api_url`、`dify_token`、`dify_dataset_id` |
| `llm_info` | `dict` | 否 | LLM 配置 |
| `share_config` | `dict` | 否 | 共享配置 |

请求示例
```json
{
    "database_name": "lightRagtestets",
    "description": "lightRagtestets是一个用于检索增强生成测试的知识库，包含多种类型的问答数据和测试文档。该知识库适合解答关于RAG系统功能验证、问答效果评估以及相关技术原理方面的问题。",
    "kb_type": "lightrag",
    "additional_params": {
        "is_private": false,
        "chunk_preset_id": "general",
        "language": "Chinese"
    },
    "embed_model_name": "siliconflow-cn:Pro/BAAI/bge-m3",
    "share_config": {
        "is_shared": true,
        "accessible_departments": []
    },
    "llm_info": {
        "provider": "siliconflow-cn:deepseek-ai",
        "model_name": "DeepSeek-V4-Flash",
        "model_spec": "siliconflow-cn:deepseek-ai/DeepSeek-V4-Flash"
    }
}
```


**响应：** 创建的知识库信息 dict。

---

#### `GET /api/knowledge/databases/accessible`

获取当前用户有权访问的知识库精简列表（普通用户可访问，用于智能体配置）。

**响应：**
```json
{
  "databases": [{"name": "str", "db_id": "str", "description": "str"}]
}
```

---

#### `GET /api/knowledge/databases/{db_id}`

获取指定知识库的详细信息。

**路径参数：**
| 参数 | 类型 | 描述 |
|------|------|------|
| `db_id` | `str` | 知识库 ID |

---

#### `PUT /api/knowledge/databases/{db_id}`

更新知识库名称、描述和配置。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `db_id` | `str` | Path | 是 | 知识库 ID |
| `name` | `str` | Body | 是 | 新名称 |
| `description` | `str` | Body | 是 | 新描述 |
| `llm_info` | `dict` | Body | 否 | LLM 配置 |
| `additional_params` | `dict \| None` | Body | 否 | 额外参数 |
| `share_config` | `dict` | Body | 否 | 共享配置 |

**响应：** `{"message": "更新成功", "database": database}`

---

#### `DELETE /api/knowledge/databases/{db_id}`

删除知识库并重新加载所有智能体。

**路径参数：**
| 参数 | 类型 | 描述 |
|------|------|------|
| `db_id` | `str` | 知识库 ID |

---

#### `GET /api/knowledge/databases/{db_id}/export`

导出知识库数据为指定格式文件。

| 参数 | 类型 | 位置 | 默认值 | 描述 |
|------|------|------|--------|------|
| `db_id` | `str` | Path | - | 知识库 ID |
| `format` | `str` | Query | `"csv"` | 导出格式: `csv`, `xlsx`, `md`, `txt` |
| `include_vectors` | `bool` | Query | `false` | 是否包含向量数据 |

**响应：** `FileResponse`（二进制文件下载）。

---

### 1.2 文档管理

#### `POST /api/knowledge/databases/{db_id}/documents`

提交文档处理异步任务（添加文件记录 → 解析文件 → 可选自动入库）。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `db_id` | `str` | Path | 是 | 知识库 ID |
| `items` | `list[str]` | Body | 是 | 文件路径列表 |
| `params` | `dict` | Body | 是 | 含 `content_type`、`auto_index`、`chunk_size`、`chunk_overlap`、`qa_separator`、`chunk_preset_id`、`chunk_parser_config` |

**响应：**
```json
{"message": "任务已提交，请在任务中心查看进度", "status": "queued", "task_id": "str"}
```

> **注意：** Dify 类型知识库不支持此操作。

---

#### `POST /api/knowledge/databases/{db_id}/documents/parse`

手动触发文档解析异步任务（仅解析，不入库）。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `db_id` | `str` | Path | 是 | 知识库 ID |
| `file_ids` | `list[str]` | Body | 是 | 文件 ID 列表 |

**响应：** `{"message": "解析任务已提交", "status": "queued", "task_id": "str"}`

---

#### `POST /api/knowledge/databases/{db_id}/documents/index`

手动触发文档入库（Indexing）异步任务。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `db_id` | `str` | Path | 是 | 知识库 ID |
| `file_ids` | `list[str]` | Body | 是 | 文件 ID 列表 |
| `params` | `dict` | Body | 否 | 入库参数（`chunk_size`、`chunk_overlap` 等） |

**响应：** `{"message": "入库任务已提交", "status": "queued", "task_id": "str"}`

---

#### `GET /api/knowledge/databases/{db_id}/documents/{doc_id}`

获取文档详细信息（含基本信息和内容信息）。

| 参数 | 类型 | 位置 | 描述 |
|------|------|------|------|
| `db_id` | `str` | Path | 知识库 ID |
| `doc_id` | `str` | Path | 文档 ID |

---

#### `GET /api/knowledge/databases/{db_id}/documents/{doc_id}/basic`

获取文档基本信息（仅元数据，不含 chunks 和 lines）。

| 参数 | 类型 | 位置 | 描述 |
|------|------|------|------|
| `db_id` | `str` | Path | 知识库 ID |
| `doc_id` | `str` | Path | 文档 ID |

---

#### `GET /api/knowledge/databases/{db_id}/documents/{doc_id}/content`

获取文档解析后的内容信息（chunks 和 lines）。

| 参数 | 类型 | 位置 | 描述 |
|------|------|------|------|
| `db_id` | `str` | Path | 知识库 ID |
| `doc_id` | `str` | Path | 文档 ID |

---

#### `DELETE /api/knowledge/databases/{db_id}/documents/batch`

批量删除文档或文件夹。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `db_id` | `str` | Path | 是 | 知识库 ID |
| `file_ids` | `list[str]` | Body | 是 | 文件/文件夹 ID 列表 |

**响应：**
```json
{"message": "批量删除成功: 已删除 N 个文件", "deleted_count": 3}
```
部分失败时：
```json
{"message": "部分删除成功: 已删除 N 个文件，失败 M 个", "deleted_count": N, "failed_items": [{"doc_id": "str", "error": "str"}]}
```

---

#### `DELETE /api/knowledge/databases/{db_id}/documents/{doc_id}`

删除单个文档或文件夹，同时清理 MinIO 中的关联文件。

| 参数 | 类型 | 位置 | 描述 |
|------|------|------|------|
| `db_id` | `str` | Path | 知识库 ID |
| `doc_id` | `str` | Path | 文档/文件夹 ID |

**响应：** `{"message": "删除成功"}` 或 `{"message": "文件夹删除成功"}`

---

#### `GET /api/knowledge/databases/{db_id}/documents/{doc_id}/download`

下载原始文件。

| 参数 | 类型 | 位置 | 描述 |
|------|------|------|------|
| `db_id` | `str` | Path | 知识库 ID |
| `doc_id` | `str` | Path | 文档 ID |

**响应：** `StreamingResponse`（二进制流，自动根据路径类型选择 MinIO 或本地下载）。

---

### 1.3 知识库查询

#### `POST /api/knowledge/databases/{db_id}/query`

对知识库执行检索查询（核心检索接口）。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `db_id` | `str` | Path | 是 | 知识库 ID |
| `query` | `str` | Body | 是 | 查询文本 |
| `meta` | `dict` | Body | 是 | 查询元数据/选项（通过 `**meta` 传入） |

**响应：** `{"result": result, "status": "success"}`

---

#### `POST /api/knowledge/databases/{db_id}/query-test`

测试查询，直接返回原始结果（少一层封装）。参数同上。

---

#### `PUT /api/knowledge/databases/{db_id}/query-params`

更新知识库的查询参数配置（如 reranker 等），持久化到数据库。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `db_id` | `str` | Path | 是 | 知识库 ID |
| `params` | `dict` | Body | 是 | 查询参数配置 |

**响应：** `{"message": "success", "data": params}`

---

#### `GET /api/knowledge/databases/{db_id}/query-params`

获取知识库类型特定的查询参数配置（合并用户已保存的配置）。

| 参数 | 类型 | 位置 | 描述 |
|------|------|------|------|
| `db_id` | `str` | Path | 知识库 ID |

**响应：** `{"params": params, "message": "success"}`

---

### 1.4 AI 示例问题

#### `POST /api/knowledge/databases/{db_id}/sample-questions`

使用 LLM 根据知识库中的文件列表自动生成测试问题，并持久化。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `db_id` | `str` | Path | 是 | 知识库 ID |
| `count` | `int` | Body | 否 | 生成问题数量，默认 10 |

**响应：**
```json
{"message": "success", "questions": ["问题1？", ...], "count": 10, "db_id": "str", "db_name": "str"}
```

---

#### `GET /api/knowledge/databases/{db_id}/sample-questions`

获取之前 AI 生成并保存的测试问题。

| 参数 | 类型 | 位置 | 描述 |
|------|------|------|------|
| `db_id` | `str` | Path | 知识库 ID |

**响应：**
```json
{"message": "success", "questions": ["问题1？", ...], "count": 2, "db_id": "str"}
```

---

### 1.5 文件管理

#### `POST /api/knowledge/databases/{db_id}/folders`

在知识库中创建文件夹。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `db_id` | `str` | Path | 是 | 知识库 ID |
| `folder_name` | `str` | Body | 是 | 文件夹名称 |
| `parent_id` | `str \| None` | Body | 否 | 父文件夹 ID |

---

#### `PUT /api/knowledge/databases/{db_id}/documents/{doc_id}/move`

移动文件或文件夹到新位置。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `db_id` | `str` | Path | 是 | 知识库 ID |
| `doc_id` | `str` | Path | 是 | 文档/文件夹 ID |
| `new_parent_id` | `str \| None` | Body | 是 | 目标父文件夹 ID |

---

#### `POST /api/knowledge/files/fetch-url`

抓取 URL 内容，保存为 HTML 上传到 MinIO。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `url` | `str` | Body | 是 | 要抓取的 URL |
| `db_id` | `str \| None` | Body | 否 | 关联的知识库 ID |

**响应：**
```json
{
  "status": "success",
  "file_path": "minio_url",
  "minio_url": "str",
  "content_hash": "str",
  "filename": "str",
  "final_url": "str",
  "size": 12345,
  "has_same_name": false,
  "same_name_files": []
}
```

---

#### `POST /api/knowledge/files/upload`

上传文件到 MinIO，检查类型支持和重复内容。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `file` | `UploadFile` | Form | 是 | 上传文件 |
| `db_id` | `str \| None` | Query | 否 | 关联的知识库 ID |
| `allow_jsonl` | `bool` | Query | 否 | 是否允许 jsonl，默认 false |

**响应：**
```json
{
  "message": "File successfully uploaded",
  "file_path": "minio_url",
  "minio_path": "minio_url",
  "db_id": "str",
  "content_hash": "str",
  "filename": "str",
  "original_filename": "str",
  "minio_filename": "str",
  "object_name": "str",
  "bucket_name": "str",
  "same_name_files": [],
  "has_same_name": false
}
```

---

#### `GET /api/knowledge/files/supported-types`

获取系统支持的所有文件扩展名列表。

**响应：** `{"message": "success", "file_types": [".pdf", ".docx", ...]}`

---

#### `POST /api/knowledge/files/markdown`

将上传文件解析为 Markdown 格式（用于预览）。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `file` | `UploadFile` | Form | 是 | 要解析的文件 |

**响应：** `{"markdown_content": "str", "message": "success"}`

---

### 1.6 类型与统计

#### `GET /api/knowledge/types`

获取系统支持的知识库类型。

**响应：** `{"kb_types": kb_types, "message": "success"}`

---

#### `GET /api/knowledge/stats`

获取所有知识库的统计信息。

**响应：** `{"stats": stats, "message": "success"}`

---

### 1.7 Embedding 模型状态

#### `GET /api/knowledge/embedding-models/{model_id}/status`

检查指定 embedding 模型的连通性和状态。

| 参数 | 类型 | 位置 | 描述 |
|------|------|------|------|
| `model_id` | `str` | Path | Embedding 模型 ID |

**响应：** `{"status": status, "message": "success"}`

---

#### `GET /api/knowledge/embedding-models/status`

检查所有可用的 embedding 模型状态。

**响应：** `{"status": {"models": {}, "total": N, "available": N}, "message": "success"}`

---

### 1.8 AI 辅助

#### `POST /api/knowledge/generate-description`

使用 LLM 生成或优化知识库描述文本。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `name` | `str` | Body | 是 | 知识库名称 |
| `current_description` | `str` | Body | 否 | 当前描述（用于优化），默认 "" |
| `file_list` | `list[str]` | Body | 否 | 文件列表，默认 [] |

**响应：** `{"description": "str", "status": "success"}`

---

## 二、知识图谱路由 (`/api/graph`)

Router 前缀: `/graph`

#### `GET /api/graph/list`

获取所有可用的知识图谱列表（包括 Neo4j Upload 和 LightRAG 知识库）。

**响应：**
```json
{
  "success": true,
  "data": [{
    "id": "neo4j | db_id",
    "name": "str",
    "type": "upload | lightrag",
    "description": "str",
    "status": "str",
    "created_at": "str",
    "node_count": 0,
    "edge_count": 0,
    "capabilities": {"supports_embedding": true, "supports_threshold": false}
  }]
}
```

---

#### `GET /api/graph/subgraph`

统一子图查询接口，根据 `db_id` 自动选择适配器。

| 参数 | 类型 | 位置 | 默认值 | 描述 |
|------|------|------|--------|------|
| `db_id` | `str` | Query | 必填 | 图谱 ID（LightRAG DB ID 或 `"neo4j"`） |
| `node_label` | `str` | Query | `"*"` | 节点标签或查询关键词 |
| `max_depth` | `int` | Query | `2` | 扩展深度 (1-5) |
| `max_nodes` | `int` | Query | `100` | 最大节点数 (1-1000) |

**响应：** `{"success": true, "data": result_data}`（图数据结构）。

---

#### `GET /api/graph/labels`

获取指定图谱的所有节点标签。

| 参数 | 类型 | 位置 | 默认值 | 描述 |
|------|------|------|--------|------|
| `db_id` | `str` | Query | 必填 | 图谱 ID |

**响应：** `{"success": true, "data": {"labels": [...]}}`

---

#### `GET /api/graph/stats`

获取图谱统计信息。

| 参数 | 类型 | 位置 | 默认值 | 描述 |
|------|------|------|--------|------|
| `db_id` | `str` | Query | 必填 | 图谱 ID |

**响应：**
```json
{
  "success": true,
  "data": {
    "total_nodes": 0,
    "total_edges": 0,
    "entity_types": [{"type": "str", "count": "N/A"}]
  }
}
```

---

#### `GET /api/graph/neo4j/nodes` [Deprecated]

> **已废弃**，请使用 `/graph/subgraph` 替代。

获取 Neo4j 图谱节点。

| 参数 | 类型 | 位置 | 默认值 | 描述 |
|------|------|------|--------|------|
| `kgdb_name` | `str` | Query | 必填 | 图数据库名称 |
| `num` | `int` | Query | `100` | 节点数量 (1-1000) |

---

#### `GET /api/graph/neo4j/node` [Deprecated]

> **已废弃**，请使用 `/graph/subgraph` 替代。

根据实体名称查询单个 Neo4j 节点。

| 参数 | 类型 | 位置 | 默认值 | 描述 |
|------|------|------|--------|------|
| `entity_name` | `str` | Query | 必填 | 实体名称 |

---

#### `GET /api/graph/neo4j/info`

获取 Neo4j 图数据库信息（状态、实体/关系数量等）。

**响应：** `{"success": true, "data": graph_info}`

---

#### `POST /api/graph/neo4j/index-entities`

为 Neo4j 图谱节点添加嵌入向量索引。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `kgdb_name` | `str` | Body | 否 | 图数据库名称，默认 `"neo4j"` |

**响应：** `{"success": true, "status": "success", "message": "已成功为N个节点添加嵌入向量", "indexed_count": 5}`

---

#### `POST /api/graph/neo4j/add-entities`

通过 JSONL 文件批量添加图实体到 Neo4j。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `file_path` | `str` | Body | 是 | JSONL 文件的 MinIO URL |
| `kgdb_name` | `str \| None` | Body | 否 | 图数据库名称 |
| `embed_model_name` | `str \| None` | Body | 否 | Embedding 模型名称 |
| `batch_size` | `int \| None` | Body | 否 | 批处理大小 |

**响应：** `{"success": true, "message": "实体添加成功", "status": "success"}`

---

## 三、知识库评估路由 (`/api/evaluation`)

Router 前缀: `/evaluation`

### 3.1 评估基准管理

#### `GET /api/evaluation/databases/{db_id}/benchmarks/{benchmark_id}`

获取指定评估基准详情，支持分页。

| 参数 | 类型 | 位置 | 默认值 | 描述 |
|------|------|------|--------|------|
| `db_id` | `str` | Path | 必填 | 知识库 ID |
| `benchmark_id` | `str` | Path | 必填 | 评估基准 ID |
| `page` | `int` | Query | `1` | 页码 |
| `page_size` | `int` | Query | `10` | 每页大小 (1-100) |

---

#### `DELETE /api/evaluation/benchmarks/{benchmark_id}`

删除评估基准。

---

#### `GET /api/evaluation/benchmarks/{benchmark_id}/download`

下载评估基准的 JSONL 文件。

**响应：** `FileResponse`。

---

#### `POST /api/evaluation/databases/{db_id}/benchmarks/upload`

上传评估基准 JSONL 文件。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `db_id` | `str` | Path | 是 | 知识库 ID |
| `file` | `UploadFile` | Form | 是 | JSONL 文件 |
| `name` | `str` | Form | 是 | 基准名称 |
| `description` | `str` | Form | 否 | 基准描述，默认 "" |

---

#### `GET /api/evaluation/databases/{db_id}/benchmarks`

获取知识库关联的所有评估基准列表。

---

#### `POST /api/evaluation/databases/{db_id}/benchmarks/generate`

自动生成评估基准（QA 对）。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `db_id` | `str` | Path | 是 | 知识库 ID |
| `params` | `dict` | Body | 是 | 生成参数配置 |

---

### 3.2 RAG 评估

#### `POST /api/evaluation/databases/{db_id}/run`

启动一次 RAG 评估任务。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `db_id` | `str` | Path | 是 | 知识库 ID |
| `benchmark_id` | `str` | Body | 是 | 评估基准 ID |
| `model_config` | `dict` | Body | 否 | 评估模型配置，默认 {} |

**响应：** `{"message": "success", "data": {"task_id": "str"}}`

---

#### `GET /api/evaluation/databases/{db_id}/results/{task_id}`

获取评估结果，支持分页和错误过滤。

| 参数 | 类型 | 位置 | 默认值 | 描述 |
|------|------|------|--------|------|
| `db_id` | `str` | Path | 必填 | 知识库 ID |
| `task_id` | `str` | Path | 必填 | 评估任务 ID |
| `page` | `int` | Query | `1` | 页码 |
| `page_size` | `int` | Query | `20` | 每页大小 (1-100) |
| `error_only` | `bool` | Query | `false` | 是否仅返回错误项 |

---

#### `DELETE /api/evaluation/databases/{db_id}/results/{task_id}`

删除评估结果。

---

#### `GET /api/evaluation/databases/{db_id}/history`

获取知识库的所有评估历史记录。

---

## 四、思维导图路由 (`/api/mindmap`)

Router 前缀: `/mindmap`

#### `GET /api/mindmap/databases/{db_id}/files`

获取指定知识库的所有文件列表。

**响应：**
```json
{"message": "success", "db_id": "str", "db_name": "str", "files": [...], "total": 0}
```

---

#### `POST /api/mindmap/generate`

使用 AI 分析知识库文件，生成思维导图。

| 参数 | 类型 | 位置 | 必填 | 描述 |
|------|------|------|------|------|
| `db_id` | `str` | Body | 是 | 知识库 ID |
| `file_ids` | `list[str]` | Body | 否 | 文件 ID 列表，默认 []（全部），最多 20 个 |
| `user_prompt` | `str` | Body | 否 | 用户自定义提示词，默认 "" |

**响应：**
```json
{"message": "success", "mindmap": mindmap_data, "db_id": "str", "db_name": "str", "file_count": 5, "original_file_count": 5, "truncated": false}
```

---

#### `GET /api/mindmap/databases`

获取所有知识库概览（含文件数量）。

**响应：**
```json
{
  "message": "success",
  "databases": [{"db_id": "str", "name": "str", "description": "str", "kb_type": "str", "file_count": 0}],
  "total": 0
}
```

---

#### `GET /api/mindmap/database/{db_id}`

获取之前生成并保存的知识库思维导图。

| 参数 | 类型 | 位置 | 描述 |
|------|------|------|------|
| `db_id` | `str` | Path | 知识库 ID |

**响应：** `{"message": "success", "mindmap": mindmap_data, "db_id": "str", "db_name": "str"}`

---

## 五、仪表盘统计 (`/api/dashboard`)

#### `GET /api/dashboard/stats/knowledge`

获取知识库聚合统计（仪表盘用）。

**响应：** `KnowledgeStats` Model
```json
{
  "total_databases": 0,
  "total_files": 0,
  "total_nodes": 0,
  "total_storage_size": 0,
  "databases_by_type": {"lightrag": 5, "milvus": 2},
  "file_type_distribution": {"PDF文件": 10, "DOCX文件": 5}
}
```

---

## 汇总

| 路由模块 | 前缀 | 端点数 | 功能域 |
|----------|------|--------|--------|
| `knowledge_router` | `/api/knowledge` | 33 | 知识库 CRUD、文档管理、检索查询、文件上传/下载、AI 辅助 |
| `graph_router` | `/api/graph` | 9 | 知识图谱列表/查询/统计/索引/批量导入 |
| `knowledge_eval_router` | `/api/evaluation` | 10 | 评估基准管理、RAG 评估运行与结果 |
| `knowledge_mindmap_router` | `/api/mindmap` | 4 | 思维导图生成与查询 |
| `dashboard_router` | `/api/dashboard` | 1 | 知识库聚合统计 |

> **权限：** 所有端点均需管理员权限。非 LITE 模式下注册 knowledge/graph/evaluation/mindmap 路由。
