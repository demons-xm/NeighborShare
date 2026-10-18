from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.db.database import get_db
from app.dependencies.auth import get_current_admin
from app.schemas.shop import ShopPublic, ShopUpdate
from app.services.shop import get_shop, update_shop

router = APIRouter(prefix="/api/shop", tags=["店铺信息"])


@router.get("", response_model=ApiResponse, summary="获取店铺信息")
async def read_shop(
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    shop = await get_shop(session)
    return ApiResponse.success(data=ShopPublic.model_validate(shop))


@router.put(
    "",
    response_model=ApiResponse,
    responses={
        401: {
            "model": ApiResponse,
            "description": "token invalid、token expired 或 no permission",
        }
    },
    summary="管理员更新店铺信息",
)
async def edit_shop(
    shop_data: ShopUpdate,
    _admin_id: str = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    shop = await update_shop(session, shop_data)
    return ApiResponse.success(
        message="店铺信息更新成功",
        data=ShopPublic.model_validate(shop),
    )
