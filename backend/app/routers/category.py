from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.db.database import get_db
from app.dependencies.auth import get_current_admin
from app.schemas.category import CategoryCreate, CategoryPublic, CategoryUpdate
from app.services.category import (
    CategoryHasDishesError,
    CategoryNotFoundError,
    create_category,
    delete_category,
    list_categories,
    update_category,
)

router = APIRouter(prefix="/api/categories", tags=["菜品分类"])


@router.get("", response_model=ApiResponse, summary="公开分类列表")
async def get_categories(
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    categories = await list_categories(session)
    return ApiResponse.success(
        data=[CategoryPublic.model_validate(item) for item in categories]
    )


@router.post(
    "",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {
            "model": ApiResponse,
            "description": "token invalid、token expired 或 no permission",
        }
    },
    summary="管理员新增分类",
)
async def post_category(
    category_data: CategoryCreate,
    _admin_id: str = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    category = await create_category(session, category_data)
    return ApiResponse.success(
        message="分类创建成功",
        data=CategoryPublic.model_validate(category),
    )


@router.put(
    "/{category_id}",
    response_model=ApiResponse,
    responses={
        401: {
            "model": ApiResponse,
            "description": "token invalid、token expired 或 no permission",
        },
        404: {"model": ApiResponse, "description": "分类不存在"},
    },
    summary="管理员编辑分类",
)
async def put_category(
    category_id: int,
    category_data: CategoryUpdate,
    _admin_id: str = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        category = await update_category(session, category_id, category_data)
    except CategoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在",
        ) from exc
    return ApiResponse.success(
        message="分类更新成功",
        data=CategoryPublic.model_validate(category),
    )


@router.delete(
    "/{category_id}",
    response_model=ApiResponse,
    responses={
        401: {
            "model": ApiResponse,
            "description": "token invalid、token expired 或 no permission",
        },
        404: {"model": ApiResponse, "description": "分类不存在"},
        409: {"model": ApiResponse, "description": "分类下仍有菜品"},
    },
    summary="管理员删除分类",
)
async def remove_category(
    category_id: int,
    _admin_id: str = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        await delete_category(session, category_id)
    except CategoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在",
        ) from exc
    except CategoryHasDishesError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="分类下仍有菜品，不能删除",
        ) from exc
    return ApiResponse.success(message="分类删除成功")
