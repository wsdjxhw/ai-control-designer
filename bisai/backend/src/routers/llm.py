"""
LLM API 路由

终版实现：B 不封装 LLM 逻辑。
B 的 router 直接调用 D 的 core/llm/* 业务模块，只做 HTTP 请求/响应转换。
B 只保留 llm_config_service 用于读写 system_settings.json。

调用关系（D 已交付，接口已确认）：
  - /llm/generate-scene   → core.llm.newbie.generate_scene(description)
  - /llm/generate-control-law → core.llm.expert.generate_initial_control_law(model_code, scene_config)
  - /llm/validate-physics → core.llm.physics_validator.validate_physics(model_code, scene_config, level)
  - /llm/parse-strategy   → core.llm.strategy_parser.parse_strategy(control_law_code)
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# D 的 core/llm 业务模块（D 已交付，B 直接调用）
from core.llm.newbie import generate_scene as newbie_generate_scene
from core.llm.expert import generate_initial_control_law as expert_generate_control_law
from core.llm.physics_validator import validate_physics as physics_validate
from core.llm.strategy_parser import parse_strategy as strategy_parse

router = APIRouter(tags=["llm"])


class GenerateSceneRequest(BaseModel):
    """新手模式：自然语言生成场景配置请求"""
    user_description: str = Field(..., description="用户用自然语言描述的物理系统")
    domain_hint: str = Field("", description="领域提示（可选，D 模块当前未使用，保留字段）")


class ValidatePhysicsRequest(BaseModel):
    """物理验证请求"""
    # 关闭 Pydantic 的 model_ 前缀保护，避免 model_code 字段告警
    model_config = {"protected_namespaces": ()}

    model_code: str = Field(..., description="模型代码文本")
    scene_config: dict = Field(default_factory=dict, description="场景配置")
    level: str = Field("L1", description="验证级别: L1(语义) | L2(符号) | L3(烟雾测试)")


class ParseStrategyRequest(BaseModel):
    """策略解析请求"""
    control_code: str = Field(..., description="控制律代码字符串")
    # D 模块的 parse_strategy 目前只用 code，params 为契约保留字段
    params: dict = Field(default_factory=dict, description="最优参数（可选）")


class ParseExpertFilesRequest(BaseModel):
    """专家模式 3 文件解析请求"""
    model_config = {"protected_namespaces": ()}

    model_code: str = Field(..., description="模型代码")
    parameters: Optional[dict] = Field(None, description="parameters.json 内容")
    env_config: Optional[dict] = Field(None, description="env.json 内容")
    description: Optional[str] = Field(None, description="可选描述")


class ParseSingleModelRequest(BaseModel):
    """单一文件解析请求"""
    model_config = {"protected_namespaces": ()}

    model_code: str = Field(..., description="完整 model.py 代码")
    description: Optional[str] = Field(None, description="可选描述")


class ValidateModelRequest(BaseModel):
    """model.py 代码验证请求"""
    model_config = {"protected_namespaces": ()}

    model_code: str = Field(..., description="完整 model.py 代码")


@router.post("/llm/generate-scene")
async def generate_scene(req: GenerateSceneRequest):
    """
    新手模式：自然语言描述 → scene_config + model_code 草案

    D 的 generate_scene(description) 内部会：
      1. 加载 newbie_guide.txt 模板组装 prompt
      2. 调用 LLM 生成 {scene_config, model_code, cost_function}
      3. 失败自动重试 3 次，最终兜底返回默认场景
    """
    try:
        result = newbie_generate_scene(req.user_description)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成场景失败: {str(e)}")


class GenerateControlLawRequest(BaseModel):
    """专家模式：基于 Model Code 生成初始控制律请求"""
    model_config = {"protected_namespaces": ()}

    model_code: str = Field(..., description="用户提供的物理建模代码")
    scene_config: dict = Field(..., description="场景配置")
    description: Optional[str] = Field(None, description="可选的自然语言描述")


@router.post("/llm/generate-control-law")
async def generate_control_law(req: GenerateControlLawRequest):
    """
    专家模式：Model Code → 初始控制律

    D 的 generate_initial_control_law(model_code, scene_config) 内部会：
      1. 构造 Prompt 描述物理系统动力学
      2. 调用 LLM 生成 control_law(t, x_grid, state, params) 函数
      3. 失败自动重试 3 次，最终兜底返回简单比例反馈
    """
    try:
        result = expert_generate_control_law(
            model_code=req.model_code,
            scene_config=req.scene_config,
            description=req.description
        )
        return {"control_law_code": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成控制律失败: {str(e)}")


@router.post("/llm/validate-physics")
async def validate_physics(req: ValidatePhysicsRequest):
    """
    物理验证（L1 LLM语义 / L2 结构检查 / L3 烟雾测试）

    D 的 validate_physics 按 level 分发：
      - L1: 调用 LLM 检查物理合理性，返回 passed/issues/suggestions
      - L2: 本地结构检查（非负约束、微分结构）
      - L3: 执行代码，实例化模型并跑 get_initial_state 烟雾测试
    """
    try:
        result = physics_validate(
            model_code=req.model_code,
            scene_config=req.scene_config,
            level=req.level,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"物理验证失败: {str(e)}")


@router.post("/llm/parse-strategy")
async def parse_strategy(req: ParseStrategyRequest):
    """
    控制策略自然语言解析

    D 的 parse_strategy(control_law_code) 返回：
      {description, key_mechanisms[], parameter_effects{}}
    前端用它把控制律代码翻译成可读的策略说明。
    """
    try:
        result = strategy_parse(req.control_code)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"策略解析失败: {str(e)}")


import ast


@router.post("/llm/validate-model")
async def validate_model_code(req: ValidateModelRequest):
    """
    使用 Python AST 深度验证 model.py 代码格式

    检查项：
    - 语法正确性
    - 继承 BaseModel
    - 实现 rhs(self, t, x, u) 方法
    - return np.array([...]) 语句
    """
    errors = []
    warnings = []

    code = req.model_code

    # 1. 语法检查
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        errors.append(f"语法错误: {e.msg} (第 {e.lineno} 行)")
        return {"valid": False, "errors": errors, "warnings": warnings}

    # 2. 检查是否有继承 BaseModel 的类
    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    has_base_model = False
    for cls in classes:
        for base in cls.bases:
            if isinstance(base, ast.Name) and base.id == 'BaseModel':
                has_base_model = True
                break
            elif isinstance(base, ast.Attribute) and base.attr == 'BaseModel':
                has_base_model = True
                break
    if not has_base_model:
        errors.append("未找到继承 BaseModel 的类定义")

    # 3. 检查是否有 __init__ 方法
    init_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == '__init__':
            init_func = node
            break

    if not init_func:
        errors.append("未找到 __init__ 方法定义（用于初始化硬编码参数）")
    else:
        # 检查 __init__ 是否有 self.xxx = ... 赋值
        has_assignment = False
        for node in ast.walk(init_func):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == 'self':
                        has_assignment = True
                        break
        if not has_assignment:
            warnings.append("__init__ 方法中未检测到 self.xxx = ... 硬编码参数赋值")

    # 5. 检查是否有 rhs 方法
    rhs_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'rhs':
            rhs_func = node
            break

    if not rhs_func:
        errors.append("未找到 rhs 方法定义")
    else:
        # 检查参数
        arg_names = [arg.arg for arg in rhs_func.args.args]
        if arg_names != ['self', 't', 'x', 'u']:
            warnings.append(f"rhs 方法参数建议为 (self, t, x, u)，当前: {arg_names}")

        # 检查是否有 return 语句
        has_return = False
        for node in ast.walk(rhs_func):
            if isinstance(node, ast.Return):
                has_return = True
                # 检查 return 是否是 np.array([...])
                if isinstance(node.value, ast.Call):
                    func = node.value.func
                    if isinstance(func, ast.Attribute):
                        if func.attr != 'array':
                            warnings.append("return 语句建议使用 np.array([...])")
                    elif isinstance(func, ast.Name):
                        if func.id != 'array':
                            warnings.append("return 语句建议使用 np.array([...])")
                break

        if not has_return:
            errors.append("rhs 方法缺少 return 语句")

    # 7. 检查是否导入了 BaseModel
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    has_import = False
    for imp in imports:
        if isinstance(imp, ast.ImportFrom):
            if imp.module and 'base_model' in imp.module:
                has_import = True
        elif isinstance(imp, ast.Import):
            for alias in imp.names:
                if 'BaseModel' in alias.name:
                    has_import = True
    if not has_import:
        warnings.append("建议显式导入: from core.models.base_model import BaseModel")

    valid = len(errors) == 0
    return {"valid": valid, "errors": errors, "warnings": warnings}



@router.post("/llm/parse-expert-files")
async def parse_expert_files(req: ParseExpertFilesRequest):
    """
    专家模式: 解析 3 个文件 (model.py + parameters.json + env.json)

    LLM 合并参数并生成完整 scene_config + 控制律
    """
    try:
        from core.llm.expert import parse_expert_mode_files

        result = parse_expert_mode_files(
            model_code=req.model_code,
            parameters=req.parameters,
            env_config=req.env_config,
            description=req.description,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")


@router.post("/llm/parse-single-model")
async def parse_single_model(req: ParseSingleModelRequest):
    """
    专家模式: 解析单一 model.py 文件

    LLM 从代码中提取硬编码参数,生成 scene_config + 控制律
    """
    try:
        from core.llm.expert import parse_single_model_file

        result = parse_single_model_file(
            model_code=req.model_code,
            description=req.description,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")