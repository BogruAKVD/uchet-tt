from collections.abc import Callable
from typing import Union

from aiogram import types
from aiogram.types import KeyboardButton

from aiogram_dialog.api.internal import RawKeyboard
from aiogram_dialog.api.protocols import DialogManager
from aiogram_dialog.widgets.kbd import Keyboard
from aiogram_dialog.widgets.text import Text

class RequestUser(Keyboard):
    def __init__(
            self,
            text: Text,
            when: Union[str, Callable, None] = None,
    ):
        super().__init__(when=when)
        self.text = text

    async def _render_keyboard(
            self,
            data: dict,
            manager: DialogManager,
    ) -> RawKeyboard:
        return [
            [
                KeyboardButton(
                    text=await self.text.render_text(data, manager),
                    request_user=types.KeyboardButtonRequestUser(
                        request_id=1),
                ),
            ],
        ]
