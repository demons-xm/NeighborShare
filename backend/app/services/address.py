from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.address import Address
from app.models.user import User
from app.schemas.address import AddressCreate, AddressUpdate


class AddressNotFoundError(Exception):
    pass


async def list_addresses(session: AsyncSession, user_id: int) -> list[Address]:
    result = await session.scalars(
        select(Address)
        .where(Address.user_id == user_id)
        .order_by(Address.is_default.desc(), Address.id.desc())
    )
    return list(result.all())


async def create_address(
    session: AsyncSession,
    user_id: int,
    address_data: AddressCreate,
) -> Address:
    await _lock_user(session, user_id)
    has_addresses = await session.scalar(
        select(Address.id).where(Address.user_id == user_id).limit(1)
    )
    make_default = address_data.is_default or has_addresses is None
    if make_default:
        await _clear_default(session, user_id)

    address = Address(
        user_id=user_id,
        **address_data.model_dump(exclude={"is_default"}),
        is_default=make_default,
    )
    session.add(address)
    await session.flush()
    return address


async def update_address(
    session: AsyncSession,
    user_id: int,
    address_id: int,
    address_data: AddressUpdate,
) -> Address:
    await _lock_user(session, user_id)
    address = await _get_owned_address(session, user_id, address_id)
    changes = address_data.model_dump(exclude_unset=True)
    requested_default = changes.pop("is_default", None)

    if requested_default is True:
        await _clear_default(session, user_id)
        address.is_default = True
    elif requested_default is False and address.is_default:
        address.is_default = False
        await session.flush()
        await _promote_oldest_address(session, user_id, exclude_id=address_id)

    for field, value in changes.items():
        setattr(address, field, value)
    await session.flush()
    return address


async def delete_address(
    session: AsyncSession,
    user_id: int,
    address_id: int,
) -> None:
    await _lock_user(session, user_id)
    address = await _get_owned_address(session, user_id, address_id)
    was_default = address.is_default
    await session.delete(address)
    await session.flush()
    if was_default:
        await _promote_oldest_address(session, user_id)


async def set_default_address(
    session: AsyncSession,
    user_id: int,
    address_id: int,
) -> Address:
    await _lock_user(session, user_id)
    address = await _get_owned_address(session, user_id, address_id)
    await _clear_default(session, user_id)
    address.is_default = True
    await session.flush()
    return address


async def _lock_user(session: AsyncSession, user_id: int) -> None:
    await session.scalar(
        select(User.id).where(User.id == user_id).with_for_update()
    )


async def _get_owned_address(
    session: AsyncSession,
    user_id: int,
    address_id: int,
) -> Address:
    address = await session.scalar(
        select(Address).where(
            Address.id == address_id,
            Address.user_id == user_id,
        )
    )
    if address is None:
        raise AddressNotFoundError
    return address


async def _clear_default(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        update(Address)
        .where(Address.user_id == user_id, Address.is_default.is_(True))
        .values(is_default=False)
    )


async def _promote_oldest_address(
    session: AsyncSession,
    user_id: int,
    exclude_id: int | None = None,
) -> None:
    query = select(Address).where(Address.user_id == user_id)
    if exclude_id is not None:
        query = query.where(Address.id != exclude_id)
    replacement = await session.scalar(query.order_by(Address.id.asc()).limit(1))
    if replacement is not None:
        replacement.is_default = True
