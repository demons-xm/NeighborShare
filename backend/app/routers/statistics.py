from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.db.database import get_db
from app.dependencies.auth import get_current_admin
from app.models.admin import Admin
from app.schemas.statistics import StatisticsPeriod
from app.services.statistics import (
    get_statistics_overview,
    resolve_statistics_range,
)

router = APIRouter(prefix="/api/admin/statistics", tags=["经营统计"])
TopN = Annotated[int, Query(ge=1, le=100)]


@router.get(
    "/overview",
    response_model=ApiResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ApiResponse,
            "description": "管理员 JWT 无效或无权限",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ApiResponse,
            "description": "统计时间范围参数不合法",
        },
    },
    summary="查询经营数据统计",
)
async def get_admin_statistics(
    period: StatisticsPeriod = "today",
    start_date: date | None = None,
    end_date: date | None = None,
    top_n: TopN = 10,
    _admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        resolved_start, resolved_end = resolve_statistics_range(
            period,
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    statistics = await get_statistics_overview(
        session,
        period,
        resolved_start,
        resolved_end,
        top_n=top_n,
    )
    return ApiResponse.success(
        message="经营统计查询成功",
        data=statistics,
    )
