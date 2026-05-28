# 知识图谱与大模型/GraphRAG 技术

> 整理日期：2026-05-28
> 目标：梳理知识图谱与大语言模型（LLM）结合的前沿技术，重点解析 GraphRAG 及其变体

---

## 一、背景：为什么需要 GraphRAG

### 1.1 传统 RAG 的局限

传统 RAG（Retrieval-Augmented Generation）基于向量相似度检索：

```
用户查询 → 向量化 → 相似度检索 → 召回文本块 → LLM 生成答案
```

**核心问题**：
1. **缺乏全局视角**：只能召回局部文本片段，难以理解文档整体结构
2. **多跳推理弱**：难以回答需要跨文档、跨段落推理的复杂问题
3. **语义鸿沟**：向量相似度 ≠ 语义关联，可能召回无关内容
4. **缺乏可解释性**：无法展示答案的知识来源路径

### 1.2 知识图谱的价值

知识图谱天然具备：
- **结构化关系**：实体间的显式关联
- **全局连通性**：可通过关系路径连接任意知识
- **多跳推理能力**：支持 "A→B→C" 的链式推理
- **可解释性**：推理路径清晰可见

### 1.3 GraphRAG 核心思想

将知识图谱与 RAG 结合，实现**从局部到全局**的增强检索：

```
┌─────────────────────────────────────────────────────┐
│                   GraphRAG 架构                      │
├─────────────────────────────────────────────────────┤
│  文档 → 知识抽取 → 知识图谱 → 社区摘要 → 全局查询   │
│         ↓                              ↓            │
│    局部检索（实体/关系）        全局检索（社区摘要）   │
│         ↓                              ↓            │
│              └────→ LLM 生成答案 ←───┘              │
└─────────────────────────────────────────────────────┘
```

---

## 二、GraphRAG 详解

### 2.1 微软 GraphRAG

Microsoft Research 于 2024 年提出的 GraphRAG 框架是最具代表性的实现。

#### 核心流程

**阶段一：索引（Indexing）**

```
1. 文本分块（Chunking）
   ↓
2. 实体抽取（Entity Extraction）
   - 抽取实体、关系、属性
   - 使用 LLM 进行零样本抽取
   ↓
3. 知识图谱构建
   - 实体消歧与合并
   - 构建图结构
   ↓
4. 社区检测（Community Detection）
   - 使用 Leiden 算法发现图社区
   - 每个社区是一组紧密关联的实体
   ↓
5. 社区摘要生成
   - 对每个社区生成自然语言摘要
   - 形成层次化的摘要结构
```

**阶段二：查询（Querying）**

```
查询类型：
├── 全局查询（Global Search）
│   └── 利用社区摘要回答宏观问题
│   └── "这些文档主要讲了什么？"
│
└── 局部查询（Local Search）
    └── 利用实体邻居关系回答具体问题
    └── "张三在哪个公司工作？"
```

#### 关键技术

1. **实体抽取 Prompt 设计**
```
任务：从文本中识别所有实体和关系

实体类型：人物、组织、地点、产品、事件
关系类型：就职于、位于、生产、参与

输出格式：
实体：{"name": "...", "type": "..."}
关系：{"source": "...", "target": "...", "relation": "..."}
```

2. **社区检测**
- 使用 **Leiden 算法** 进行层次化社区发现
- 支持不同粒度（level 0 ~ level N）
- 高层社区更宏观，低层社区更具体

3. **混合检索**
- 全局摘要 + 局部图结构
- 向量检索 + 图遍历

### 2.2 LightRAG

LightRAG 是一个轻量级、模块化的 GraphRAG 框架。

#### 特点

| 特性 | GraphRAG（微软） | LightRAG |
|------|----------------|----------|
| 架构复杂度 | 高（社区检测+层次摘要） | 低（简单图结构） |
| 索引速度 | 慢 | 快 |
| 存储需求 | 大 | 小 |
| 检索模式 | 全局+局部 | 局部为主 |
| 适用场景 | 大规模文档集 | 中小型项目 |

#### 核心设计

```python
# LightRAG 核心流程
class LightRAG:
    def __init__(self, llm, embedding_model, graph_storage, vector_storage):
        self.llm = llm
        self.embedding = embedding_model
        self.graph = graph_storage      # 图存储（Neo4j/MemGraph）
        self.vector = vector_storage    # 向量存储

    def insert(self, text):
        # 1. 抽取实体和关系
        entities, relations = self.llm.extract(text)
        # 2. 存入图数据库
        self.graph.add_entities(entities)
        self.graph.add_relations(relations)
        # 3. 存入向量数据库（用于文本块检索）
        self.vector.add(text)

    def query(self, question):
        # 1. 从问题中抽取关键实体
        query_entities = self.llm.extract_entities(question)
        # 2. 图遍历获取相关子图
        subgraph = self.graph.get_neighborhood(query_entities)
        # 3. 向量检索获取相关文本
        texts = self.vector.search(question)
        # 4. LLM 生成答案
        return self.llm.generate(question, context=subgraph + texts)
```

### 2.3 其他 GraphRAG 方案

| 方案 | 特点 | 来源 |
|------|------|------|
| **GraphRAG（微软）** | 社区检测+层次摘要，全局+局部查询 | Microsoft Research |
| **LightRAG** | 轻量、模块化、易扩展 | 开源社区 |
| **NanoGraphRAG** | 极简实现，100行代码 | 开源社区 |
| **HippoRAG** | 受海马体记忆启发的图索引 | 学术研究 |
| **LazyGraphRAG** | 延迟构建图索引 | 开源社区 |
| **FastGraphRAG** | 性能优化版 | 开源社区 |

---

## 三、GraphRAG vs 传统 RAG

### 3.1 能力对比

| 能力 | 传统 RAG | GraphRAG |
|------|---------|----------|
| 单跳问答 | ✅ | ✅ |
| 多跳推理 | ❌ | ✅ |
| 全局摘要 | ❌ | ✅ |
| 关系推理 | ❌ | ✅ |
| 可解释性 | 低 | 高 |
| 结构化数据 | 弱 | 强 |
| 构建成本 | 低 | 高 |
| 查询延迟 | 低 | 中高 |

### 3.2 适用场景

**选择传统 RAG**：
- 简单问答场景
- 数据量小、关系简单
- 对延迟敏感
- 资源有限

**选择 GraphRAG**：
- 复杂多跳推理
- 需要全局洞察
- 关系密集型数据
- 对可解释性要求高

---

## 四、GraphRAG 实战：LangChain + Neo4j

### 4.1 环境准备

```bash
pip install langchain langchain-openai neo4j
```

### 4.2 基础实现

```python
from langchain_community.graphs import Neo4jGraph
from langchain_openai import ChatOpenAI
from langchain.chains import GraphCypherQAChain

# 1. 连接 Neo4j
graph = Neo4jGraph(
    url="bolt://localhost:7687",
    username="neo4j",
    password="password"
)

# 2. 使用 LLM 自动构建知识图谱
llm = ChatOpenAI(model="gpt-4")

# 从文档中抽取并构建图谱
from langchain_experimental.graph_transformers import LLMGraphTransformer

transformer = LLMGraphTransformer(llm=llm)
# documents = load_your_documents()
# graph_documents = transformer.convert_to_graph_documents(documents)
# graph.add_graph_documents(graph_documents)

# 3. 图查询 QA
chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    verbose=True
)

result = chain.run("阿里巴巴的创始人是谁？")
```

### 4.3 GraphRAG 完整流程

```python
import lightrag  # 或自研实现

# 1. 初始化
rag = LightRAG(
    working_dir="./kg_storage",
    llm_model_func=gpt4_completion,
    embedding_func=openai_embedding
)

# 2. 插入文档
rag.insert("阿里巴巴由马云于1999年创立...")
rag.insert("马云毕业于杭州师范大学...")
rag.insert("阿里巴巴总部在杭州...")

# 3. 查询（自动使用图增强检索）
result = rag.query(
    "阿里巴巴创始人的教育背景是什么？",
    param=QueryParam(mode="hybrid")  # hybrid = 向量+图
)
print(result)
# 输出：马云毕业于杭州师范大学...
```

---

## 五、2025-2026 GraphRAG 技术趋势

### 5.1 研究方向

1. **动态图 RAG**：支持实时更新的知识图谱
2. **多模态 GraphRAG**：融合文本、图像、视频知识
3. **Agentic GraphRAG**：让 Agent 自主探索图结构
4. **轻量级 GraphRAG**：降低构建和查询成本
5. **融合向量+图+关键词**：Hybrid RAG 成为主流

### 5.2 企业落地实践

| 企业 | 实践 |
|------|------|
| **微软** | GraphRAG 开源框架，Azure 集成 |
| **蚂蚁集团** | 金融知识图谱 + 大模型风控 |
| **创邻科技** | 知寰 Hybrid RAG，企业私域知识 |
| **Neo4j** | LLM Knowledge Graph Builder |

---

## 六、参考链接

- [(88页)知识图谱增强大模型 GraphRAG 2025 调研综述](https://blog.csdn.net/m0_59235945/article/details/145122508)
- [什么是 GraphRAG？- 腾讯云](https://cloud.tencent.com/developer/article/2647990)
- [2026 GraphRAG 方案盘点](https://www.toutiao.com/article/7599989358678065683/)
- [知识图谱增强 RAG 最佳实践报告 - 沙丘智库](https://www.shaqiu.cn/article/AGlZV5DxLBJm)
- [用 Neo4j 与 LangChain 实现 GraphRAG - 知乎](https://zhuanlan.zhihu.com/p/709060837)
- [知识图谱三强争霸：Neo4j/LightRAG/GraphRAG PK](https://www.cnblogs.com/gccbuaa/p/19168056)
- [LightRAG 实战 - 阿里云](https://developer.aliyun.com/article/1688135)
