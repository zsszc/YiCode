from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db as _get_db
from app.core.security import decode_access_token
from app.config import get_settings
from app.models.user import User


# OAuth2 scheme for token extraction from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_db() -> Session:
    """FastAPI dependency: 数据库 session。"""
    yield from _get_db()


def get_settings_dep():
    """FastAPI dependency: 应用配置。"""
    return get_settings()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: 获取当前登录用户。
    
    如果未提供 token 或 token 无效，返回默认用户 (id=1) 以保持向后兼容。
    生产环境应改为抛出 401 异常。
    """
    # 向后兼容：没有 token 时返回默认用户
    if not token:
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            # 创建默认用户
            user = User(id=1, username="default")
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    payload = decode_access_token(token)
    if not payload:
        # 无效 token：返回默认用户（向后兼容模式）
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            user = User(id=1, username="default")
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    user_id = int(payload.get("sub", 1))
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


def get_current_user_strict(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """严格模式：必须提供有效 token，否则 401。"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证 token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user
