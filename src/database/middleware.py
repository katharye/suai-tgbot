from vkbottle import BaseMiddleware

from database.engine import async_session


class DbSessionMiddleware(BaseMiddleware):
    """Открывает сессию БД на каждое событие (сообщение или нажатие кнопки)
    и прокидывает её в хендлер как параметр `session`, как это было в aiogram.
    """

    async def pre(self) -> None:
        self._session_ctx = async_session()
        session = await self._session_ctx.__aenter__()
        self.send({"session": session})

    async def post(self) -> None:
        await self._session_ctx.__aexit__(None, None, None)
