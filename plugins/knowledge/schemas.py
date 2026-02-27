"""
Knowledge Extraction/Analysis JSON Schemas

集中定义所有 LLM 提取/分析任务的 JSON Schema，
供 BaseAgent.call_llm_structured() 使用。
"""

CONTRIBUTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "contributions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "贡献简短标题"},
                    "description": {"type": "string", "description": "详细描述"},
                    "novelty": {"type": "string", "description": "创新点说明"},
                    "significance": {"type": "string", "description": "重要性评估"},
                },
                "required": ["title", "description"],
            },
        }
    },
    "required": ["contributions"],
}

METHODOLOGY_SCHEMA = {
    "type": "object",
    "properties": {
        "approach": {"type": "string", "description": "总体方法概述"},
        "techniques": {
            "type": "array",
            "items": {"type": "string"},
            "description": "使用的技术列表",
        },
        "model_architecture": {"type": "string", "description": "模型架构描述"},
        "datasets": {
            "type": "array",
            "items": {"type": "string"},
            "description": "使用的数据集",
        },
        "evaluation_metrics": {
            "type": "array",
            "items": {"type": "string"},
            "description": "评估指标",
        },
        "implementation_details": {"type": "string", "description": "实现细节"},
    },
    "required": ["approach", "techniques"],
}

RESEARCH_QUESTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "research_questions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "核心研究问题列表",
        }
    },
    "required": ["research_questions"],
}

FINDINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "finding": {"type": "string", "description": "发现描述"},
                    "evidence": {"type": "string", "description": "支持证据"},
                    "importance": {"type": "string", "description": "重要性"},
                },
                "required": ["finding"],
            },
        },
        "performance_improvements": {"type": "string", "description": "性能提升总结"},
    },
    "required": ["findings"],
}

LIMITATIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "limitations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "局限性列表",
        }
    },
    "required": ["limitations"],
}

FUTURE_WORK_SCHEMA = {
    "type": "object",
    "properties": {
        "future_work": {"type": "string", "description": "未来工作方向的总结"},
        "open_questions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "开放问题列表",
        },
    },
    "required": ["future_work"],
}

KEYWORDS_SCHEMA = {
    "type": "object",
    "properties": {
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "关键词列表",
        }
    },
    "required": ["keywords"],
}

CONCEPTS_SCHEMA = {
    "type": "object",
    "properties": {
        "concepts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "概念名称"},
                    "definition": {"type": "string", "description": "概念定义"},
                    "role": {"type": "string", "description": "在论文中的作用"},
                },
                "required": ["name", "definition"],
            },
        }
    },
    "required": ["concepts"],
}

TOPICS_SCHEMA = {
    "type": "object",
    "properties": {
        "primary_field": {"type": "string", "description": "主要研究领域"},
        "sub_fields": {
            "type": "array",
            "items": {"type": "string"},
            "description": "子领域",
        },
        "research_direction": {"type": "string", "description": "具体研究方向"},
        "technical_stack": {
            "type": "array",
            "items": {"type": "string"},
            "description": "技术栈",
        },
        "application_domains": {
            "type": "array",
            "items": {"type": "string"},
            "description": "应用领域",
        },
    },
    "required": ["primary_field", "research_direction"],
}

EVOLUTION_SCHEMA = {
    "type": "object",
    "properties": {
        "builds_on": {"type": "string", "description": "基于哪些前人工作"},
        "innovation": {"type": "string", "description": "主要创新点"},
        "potential_impact": {"type": "string", "description": "潜在影响"},
        "position_in_timeline": {"type": "string", "description": "在研究时间线中的位置"},
    },
    "required": ["builds_on", "innovation"],
}

COMPARE_PAPERS_SCHEMA = {
    "type": "object",
    "properties": {
        "commonalities": {
            "type": "array",
            "items": {"type": "string"},
        },
        "differences": {
            "type": "array",
            "items": {"type": "string"},
        },
        "comparative_advantages": {
            "type": "object",
            "description": "各论文的比较优势",
        },
        "relationship": {"type": "string", "description": "竞争/互补/延续"},
        "summary": {"type": "string", "description": "对比总结"},
    },
    "required": ["commonalities", "differences", "summary"],
}

INGESTION_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "简洁的论文总结（3-5句话）"},
        "research_area": {"type": "string", "description": "研究领域"},
        "paper_type": {"type": "string", "description": "论文类型（empirical/theoretical/survey/system）"},
    },
    "required": ["summary", "research_area", "paper_type"],
}

VERIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "is_accurate": {"type": "boolean", "description": "提取结果是否准确"},
        "confidence": {"type": "number", "description": "置信度 0-1"},
        "corrections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "issue": {"type": "string"},
                    "corrected_value": {},
                },
                "required": ["field", "issue"],
            },
        },
        "corrected_data": {"type": "object", "description": "修正后的完整数据"},
    },
    "required": ["is_accurate", "confidence"],
}

ENHANCE_IDEA_SCHEMA = {
    "type": "object",
    "properties": {
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "提取的标签",
        },
        "refined_content": {"type": "string", "description": "完善后的内容"},
    },
    "required": ["tags", "refined_content"],
}
