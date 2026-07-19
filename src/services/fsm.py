from typing import Any

from vkbottle import BaseStateGroup, BuiltinStateDispenser

# Единый диспенсер состояний для всего бота. Создаётся один раз здесь и
# передаётся в Bot(state_dispenser=state_dispenser) в main.py, чтобы все
# хендлеры (message и message_event) работали с одним и тем же хранилищем.
state_dispenser = BuiltinStateDispenser()


async def get_state(peer_id: int) -> str | None:
    """Вернуть текущее состояние пользователя (или None)."""
    peer = await state_dispenser.get(peer_id)
    return peer.state if peer is not None else None


def is_state(current: str | None, *groups: BaseStateGroup) -> bool:
    """Надёжно сравнить текущее состояние с одним или несколькими BaseStateGroup.

    pydantic-модель StatePeer иногда приводит сохранённое состояние к обычной
    `str`, теряя переопределённый `StateRepresentation.__eq__` — из-за этого
    прямое `current == SomeGroup.member` может внезапно вернуть False, хотя
    строковое содержимое совпадает. Поэтому всегда сравниваем через str(...).
    """
    if current is None:
        return False
    return any(str(current) == str(g) for g in groups)


async def get_state_data(peer_id: int) -> dict[str, Any]:
    """Аналог FSMContext.get_data() из aiogram."""
    peer = await state_dispenser.get(peer_id)
    return dict(peer.payload) if peer is not None else {}


async def set_state(peer_id: int, state: BaseStateGroup, **data: Any) -> None:
    """Аналог FSMContext.set_state(), опционально сразу с данными."""
    await state_dispenser.set(peer_id, state, **data)


async def update_state_data(peer_id: int, **data: Any) -> dict[str, Any]:
    """Аналог FSMContext.update_data(): дополняет payload текущего состояния."""
    peer = await state_dispenser.get(peer_id)
    if peer is None:
        return dict(data)
    merged = {**peer.payload, **data}
    await state_dispenser.set(peer_id, peer.state, **merged)
    return merged


async def clear_state(peer_id: int) -> None:
    """Аналог FSMContext.clear()."""
    await state_dispenser.delete(peer_id)


async def advance_state(peer_id: int, new_state: BaseStateGroup, **extra: Any) -> dict[str, Any]:
    """Переход в новое состояние с сохранением уже накопленных в payload данных
    (аналог set_state() в aiogram, который не затирает data, накопленную через update_data())."""
    peer = await state_dispenser.get(peer_id)
    merged = {**(peer.payload if peer is not None else {}), **extra}
    await state_dispenser.set(peer_id, new_state, **merged)
    return merged
