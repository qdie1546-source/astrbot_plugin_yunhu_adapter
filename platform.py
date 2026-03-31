import asyncio
from typing import Dict, Any, List, Union
from astrbot.api.platform import Platform, AstrMessageEvent, AstrBotMessage, MessageMember
from astrbot.api.message_components import Plain, Image, At
from astrbot.api import logger
from yunhu import YunHuClient
from yunhu.models import TextMessage, ImageMessage, AtMessage

class YunHuPlatform(Platform):
    def __init__(self, context, token: str, base_url: str, ws_url: str = None):
        super().__init__(context)
        self.token = token
        self.base_url = base_url
        self.ws_url = ws_url
        self.client = YunHuClient(token=token, base_url=base_url, websocket_url=ws_url)
        self._running = False
        self._ws_task = None

    async def run(self):
        await self.client.start()
        self._running = True
        if self.ws_url:
            self.client.on('message', self._on_message)
            self._ws_task = asyncio.create_task(self.client.start_event_stream())
            logger.info("云湖平台已启动（WebSocket模式）")
        else:
            logger.info("云湖平台已启动（仅HTTP发送）")

    async def stop(self):
        self._running = False
        if self._ws_task:
            self._ws_task.cancel()
        await self.client.close()

    async def send_message(self, event: AstrMessageEvent):
        message = event.message_obj
        chat_id = message.session_id
        content = self._convert_chain_to_yunhu(message.message)
        if not content:
            return
        try:
            await self.client.send_message(chat_id, content)
        except Exception as e:
            logger.exception(f"发送消息失败: {e}")

    def _convert_chain_to_yunhu(self, chain: List) -> Union[TextMessage, ImageMessage, AtMessage, None]:
        texts = []
        for comp in chain:
            if isinstance(comp, Plain):
                texts.append(comp.text)
            elif isinstance(comp, Image):
                return ImageMessage(url=comp.file)
            elif isinstance(comp, At):
                return AtMessage(user_id=comp.qq)
        if texts:
            return TextMessage(text=' '.join(texts))
        return None

    async def process_webhook(self, data: Dict[str, Any]):
        """处理云湖推送的 webhook 消息"""
        # 示例：根据实际推送格式调整
        try:
            msg_data = data.get('message', {})
            chat_id = msg_data.get('chat_id')
            text = msg_data.get('text')
            sender_id = msg_data.get('sender', {}).get('id')
            sender_name = msg_data.get('sender', {}).get('name')
            is_group = chat_id != sender_id

            if not chat_id or not text:
                logger.debug("webhook消息缺少必要字段")
                return

            astr_msg = AstrBotMessage()
            astr_msg.type = "group" if is_group else "private"
            astr_msg.self_id = ""
            astr_msg.session_id = chat_id
            astr_msg.message_id = data.get('message_id', '')
            astr_msg.group_id = chat_id if is_group else ""
            astr_msg.sender = MessageMember(user_id=sender_id, nickname=sender_name)
            astr_msg.message = [Plain(text)]
            astr_msg.message_str = text
            astr_msg.timestamp = int(data.get('timestamp', 0))

            astr_event = AstrMessageEvent(
                platform_name="yunhu",
                message_obj=astr_msg,
                platform=self
            )
            await self.context.message_dispatcher.dispatch(astr_event)
        except Exception as e:
            logger.exception("处理 webhook 消息失败")

    async def _on_message(self, event):
        pass