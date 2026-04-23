import json
from typing import Any, Optional

from langchain_core.tools import StructuredTool
from pydantic import Field, create_model


def mcp_result_to_text(result: Any) -> str:
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return json.dumps(structured, ensure_ascii=False, indent=2)

    content = getattr(result, "content", None)
    if content:
        parts: list[str] = []
        for block in content:
            text = getattr(block, "text", None)
            if text is not None:
                parts.append(str(text))
            else:
                parts.append(str(block))
        return "\n".join(parts)

    return str(result)


def _schema_type_to_python(prop: dict[str, Any]) -> Any:
    type_map = {"string": str, "integer": int, "number": float, "boolean": bool}
    schema_type = prop.get("type")
    if isinstance(schema_type, list):
        schema_type = next((item for item in schema_type if item != "null"), "string")
    return type_map.get(schema_type, str)


def mcp_tools_to_langchain(mcp_tools: list[Any], mcp_client: Any) -> list[StructuredTool]:
    """Convert FastMCP tool definitions to LangChain StructuredTool objects."""
    lc_tools: list[StructuredTool] = []
    for tool in mcp_tools:
        schema = tool.inputSchema or {"type": "object", "properties": {}}
        props = schema.get("properties", {})
        required = set(schema.get("required", []))

        fields: dict[str, tuple[Any, Field]] = {}
        for name, prop in props.items():
            py_type = _schema_type_to_python(prop)
            default = ... if name in required else prop.get("default")
            field_type = py_type if name in required else Optional[py_type]
            fields[name] = (
                field_type,
                Field(default=default, description=prop.get("description", "")),
            )

        args_model = create_model(f"{tool.name}_args", **fields) if fields else None
        tool_name = tool.name

        async def _invoke(_name: str = tool_name, **kwargs: Any) -> str:
            result = await mcp_client.call_tool(_name, kwargs)
            return mcp_result_to_text(result)

        lc_tools.append(
            StructuredTool.from_function(
                coroutine=_invoke,
                name=tool.name,
                description=tool.description or tool.name,
                args_schema=args_model,
            )
        )

    return lc_tools
