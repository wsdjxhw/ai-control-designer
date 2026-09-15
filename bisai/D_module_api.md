# D模块 API 接口说明

本文档描述 D 模块（LLM/RAG 智能层）对外提供的所有接口。

---

## 1. 策略语义检索

**路由：** `POST /api/v1/rag/search`

**入参：**
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | ✅ | 检索文本 |
| top_k | integer | ❌ | 返回数量，默认 5 |
| filters | object | ❌ | 过滤条件，支持 domain 过滤 |

**出参：**
| 字段 | 类型 | 说明 |
|------|------|------|
| results | array | 检索结果列表 |
| results[].id | string | 策略唯一标识 |
| results[].code | string | 控制律代码全文 |
| results[].metadata | object | 元数据（domain, version, cost, params, created_at） |
| results[].similarity | number | 相似度 0~1 |

---

## 2. 策略入库

**路由：** `POST /api/v1/rag/store`

**入参：**
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | ✅ | 策略唯一标识，如 uwsn_v12 |
| code | string | ✅ | 控制律代码全文 |
| metadata.domain | string | ✅ | 领域名称 |
| metadata.version | integer | ✅ | 版本号 |
| metadata.cost | number | ✅ | 总代价 |
| metadata.params | object | ✅ | 最优参数 |

**出参：**
| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 是否成功 |
| message | string | 信息 |

---

## 3. 新手模式生成场景

**路由：** `POST /api/v1/llm/generate-scene`

**入参：**
| 字段 | 类型 | 说明 |
|------|------|------|
| description | string | 用户自然语言描述 |

**出参：**
| 字段 | 类型 | 说明 |
|------|------|------|
| scene_config | object | 场景配置 |
| model_code | string | 模型代码 |
| cost_function | object | 代价函数建议 |

---

## 4. 物理验证

**路由：** `POST /api/v1/llm/validate-physics`

**入参：**
| 字段 | 类型 | 说明 |
|------|------|------|
| model_code | string | 模型代码 |
| scene_config | object | 场景配置 |
| level | string | L1/L2/L3，默认 L1 |

**出参：**
| 字段 | 类型 | 说明 |
|------|------|------|
| L1 | boolean | L1 验证是否通过 |
| L2 | boolean | L2 验证是否通过 |
| L3 | boolean | L3 验证是否通过 |
| details | string | 详细信息 |

---

## 5. 策略解析

**路由：** `POST /api/v1/llm/parse-strategy`

**入参：**
| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 控制律代码 |
| params | object | 最优参数 |

**出参：**
| 字段 | 类型 | 说明 |
|------|------|------|
| description | string | 策略描述 |
| key_mechanisms | array | 关键机制 |
| parameter_effects | object | 参数作用 |