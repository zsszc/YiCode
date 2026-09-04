from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def get_me():
    """获取当前用户信息（Phase 1 预留，返回默认用户）。"""
    return {
        "id": 1,
        "username": "default",
        "email": None,
    }
