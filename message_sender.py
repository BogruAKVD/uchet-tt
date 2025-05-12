from aiogram import Bot
from aiogram.types import InputFile, InputMediaPhoto, InputMediaDocument, InputMediaVideo, InputMediaAnimation
from aiogram.enums import ParseMode
from aiogram.exceptions import AiogramError
from typing import Optional, List, Dict, Any



class MessageSender:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_message(
            self,
            user_id: int,
            message: str,
            parse_mode: Optional[str] = ParseMode.HTML,
            disable_notification: bool = False,
            disable_web_page_preview: bool = False,
            media_path: Optional[str] = None,
            media_type: Optional[str] = None,
            media_caption: Optional[str] = None,
            media_group: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Отправляет сообщение или медиа пользователю

        :param user_id: ID пользователя
        :param message: Текст сообщения
        :param parse_mode: Режим парсинга (HTML/Markdown)
        :param disable_notification: Отключить уведомление
        :param disable_web_page_preview: Отключить превью веб-страниц
        :param media_path: Путь к файлу или URL медиа
        :param media_type: Тип медиа (photo, video, animation, document)
        :param media_caption: Подпись к медиа (если None, используется message)
        :param media_group: Список медиа для отправки как группа (переопределяет media_path/media_type)
        :return: True если сообщение/медиа отправлено успешно, False в случае ошибки
        """
        try:
            if media_group:
                media_list = []
                for media_item in media_group:
                    media_class = self._get_media_class(media_item['type'])
                    media_list.append(media_class(
                        media=media_item['path'],
                        caption=media_item.get('caption', ''),
                        parse_mode=parse_mode
                    ))
                await self.bot.send_media_group(
                    chat_id=user_id,
                    media=media_list,
                    disable_notification=disable_notification
                )
            elif media_path and media_type:
                # Отправка одиночного медиа
                caption = media_caption if media_caption is not None else message
                method = self._get_send_method(media_type)
                await method(
                    chat_id=user_id,
                    caption=caption,
                    parse_mode=parse_mode,
                    disable_notification=disable_notification,
                    **{media_type: InputFile(media_path) if not media_path.startswith(('http://', 'https://')) else media_path}
                )
            else:
                # Отправка обычного текстового сообщения
                await self.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=parse_mode,
                    disable_notification=disable_notification,
                    disable_web_page_preview=disable_web_page_preview
                )
            return True
        except AiogramError as e:
            print(f"Failed to send message to user {user_id}: {e}")
            return False

    def _get_send_method(self, media_type: str):
        """Возвращает метод отправки для указанного типа медиа"""
        methods = {
            'photo': self.bot.send_photo,
            'video': self.bot.send_video,
            'animation': self.bot.send_animation,
            'document': self.bot.send_document,
            'audio': self.bot.send_audio,
            'voice': self.bot.send_voice
        }
        return methods.get(media_type, self.bot.send_message)

    def _get_media_class(self, media_type: str):
        """Возвращает класс медиа для медиагруппы"""
        classes = {
            'photo': InputMediaPhoto,
            'video': InputMediaVideo,
            'animation': InputMediaAnimation,
            'document': InputMediaDocument
        }
        return classes.get(media_type, InputMediaPhoto)
