from fastapi import APIRouter

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("")
async def list_tools():
    from tools.quant.technical.interface import list_tools as _list_tools
    tools_dict = _list_tools()
    return [
        {"name": name, "description": tool.description}
        for name, tool in tools_dict.items()
    ]
