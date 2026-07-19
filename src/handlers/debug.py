"""Временный модуль для диагностики: логирует все входящие события.

Не мешает обычной обработке (blocking=False), просто печатает в консоль
всё, что реально прилетает от VK. Можно удалить после отладки.
"""

from vkbottle import GroupEventType
from vkbottle.bot import BotLabeler, Message, MessageEvent

debug_labeler = BotLabeler()


@debug_labeler.message(blocking=False)
async def log_message(message: Message):
    print(
        f"[DEBUG message_new] text={message.text!r} "
        f"payload={message.get_payload_json()!r} "
        f"from_id={message.from_id} peer_id={message.peer_id}"
    )


@debug_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, blocking=False)
async def log_message_event(event: MessageEvent):
    print(f"[DEBUG message_event] payload={event.payload!r} peer_id={event.peer_id}")
