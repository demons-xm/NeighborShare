from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import config

engine_options = {"echo": False, "pool_pre_ping": True}
if not config.DATABASE_URL.startswith("sqlite"):
    engine_options.update(pool_size=10, max_overflow=20)

async_engine = create_async_engine(config.DATABASE_URL, **engine_options)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,  # 绑定到之前创建的异步引擎
    class_=AsyncSession,  # 指定会话类为 AsyncSession
    expire_on_commit=False  # 提交后不使对象属性过期，保持数据可访问
)


# 依赖项，用于获取数据库会话
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session  # 将会话对象产出给调用者，暂停函数执行直到请求结束
            await session.commit()  # 如果无异常，提交事务
        except Exception:
            await session.rollback()  # 发生异常时回滚事务
            raise  # 重新抛出异常以便上层处理
        finally:
            await session.close()  # 关闭会话，释放资源


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="主键ID"
    )
    create_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="创建时间"
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
