from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.db.database import get_db
from app.dependencies.auth import get_current_admin
from app.schemas.dish import (
    DishAvailabilityUpdate,
    DishCreate,
    DishPublic,
    DishUpdate,
)
from app.services.dish import (
    DishCategoryNotFoundError,
    DishNotFoundError,
    create_dish,
    delete_dish,
    get_available_dish,
    list_admin_dishes,
    list_available_dishes,
    set_dish_availability,
    update_dish,
)

router = APIRouter(tags=["菜品"])


@router.get("/api/dishes", response_model=ApiResponse, summary="获取上架菜品列表")
async def get_dishes(
    category_id: int | None = Query(default=None, gt=0),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    dishes = await list_available_dishes(session, category_id)
    return ApiResponse.success(
        data=[DishPublic.model_validate(dish) for dish in dishes]
    )


@router.get(
    "/api/dishes/{dish_id}",
    response_model=ApiResponse,
    responses={404: {"model": ApiResponse, "description": "菜品不存在或已下架"}},
    summary="获取菜品详情",
)
async def get_dish(
    dish_id: int,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        dish = await get_available_dish(session, dish_id)
    except DishNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="菜品不存在或已下架",
        ) from exc
    return ApiResponse.success(data=DishPublic.model_validate(dish))


@router.get(
    "/api/admin/dishes",
    response_model=ApiResponse,
    summary="管理员查询全部菜品",
)
async def get_admin_dishes(
    category_id: int | None = Query(default=None, gt=0),
    is_available: bool | None = None,
    _admin_id: str = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    dishes = await list_admin_dishes(session, category_id, is_available)
    return ApiResponse.success(
        data=[DishPublic.model_validate(dish) for dish in dishes]
    )


@router.post(
    "/api/admin/dishes",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ApiResponse, "description": "管理员 JWT 无效或无权限"},
        404: {"model": ApiResponse, "description": "菜品分类不存在"},
    },
    summary="管理员新增菜品",
)
async def post_dish(
    dish_data: DishCreate,
    _admin_id: str = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        dish = await create_dish(session, dish_data)
    except DishCategoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="菜品分类不存在",
        ) from exc
    return ApiResponse.success(
        message="菜品创建成功",
        data=DishPublic.model_validate(dish),
    )


@router.put(
    "/api/admin/dishes/{dish_id}",
    response_model=ApiResponse,
    responses={
        401: {"model": ApiResponse, "description": "管理员 JWT 无效或无权限"},
        404: {"model": ApiResponse, "description": "菜品或分类不存在"},
    },
    summary="管理员编辑菜品",
)
async def put_dish(
    dish_id: int,
    dish_data: DishUpdate,
    _admin_id: str = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        dish = await update_dish(session, dish_id, dish_data)
    except DishNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="菜品不存在",
        ) from exc
    except DishCategoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="菜品分类不存在",
        ) from exc
    return ApiResponse.success(
        message="菜品更新成功",
        data=DishPublic.model_validate(dish),
    )


@router.patch(
    "/api/admin/dishes/{dish_id}/availability",
    response_model=ApiResponse,
    responses={
        401: {"model": ApiResponse, "description": "管理员 JWT 无效或无权限"},
        404: {"model": ApiResponse, "description": "菜品不存在"},
    },
    summary="管理员上架或下架菜品",
)
async def patch_dish_availability(
    dish_id: int,
    update_data: DishAvailabilityUpdate,
    _admin_id: str = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        dish = await set_dish_availability(
            session,
            dish_id,
            update_data.is_available,
        )
    except DishNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="菜品不存在",
        ) from exc
    message = "菜品已上架" if dish.is_available else "菜品已下架"
    return ApiResponse.success(
        message=message,
        data=DishPublic.model_validate(dish),
    )


@router.delete(
    "/api/admin/dishes/{dish_id}",
    response_model=ApiResponse,
    responses={
        401: {"model": ApiResponse, "description": "管理员 JWT 无效或无权限"},
        404: {"model": ApiResponse, "description": "菜品不存在"},
    },
    summary="管理员删除菜品",
)
async def remove_dish(
    dish_id: int,
    _admin_id: str = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        await delete_dish(session, dish_id)
    except DishNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="菜品不存在",
        ) from exc
    return ApiResponse.success(message="菜品删除成功")
