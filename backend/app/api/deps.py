from fastapi import Depends, Header, HTTPException, status

from app.core.config import settings
from app.core.security import decode_access_token


def get_current_admin(authorization: str | None = Header(default=None)) -> str:
    """管理员鉴权依赖。

    前端请求管理员接口时需要传入 `Authorization: Bearer <token>`。
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录管理员账号")

    token = authorization.removeprefix("Bearer ").strip()
    subject = decode_access_token(token)
    if subject != settings.admin_username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="管理员身份无效")
    return subject

