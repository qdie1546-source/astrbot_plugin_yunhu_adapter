import asyncio
from typing import Dict, Any, List, Union
from astrbot.api.platform import Platform, AstrMessageEvent, AstrBotMessage, MessageMember
from astrbot.api.message_components import Plain, Image, At
from astrbot.api import logger
from yunhu import YunHuClient
from yunhu.models import TextMessage, ImageMessage, AtMessage

class YunHuPlatform(Platform):
    def __init__(self, context, event_queue):
        # 正确接收框架传入的 context 和 event_queue
        super().__init__(context, event_queue)
        self.client = None
        self.config = {}
        self._running = False
        self._ws_task = None

    def meta(self) -> dict:
        return {
            "name": "yunhu",
            "display_name": "云湖IM",
            "description": "云湖官方机器人适配器，支持 token 认证和 webhook/WebSocket 消息接收",
            "config_schema": [
                {
                    "key": "token",
                    "label": "云湖 Token",
                    "type": "string",
                    "required": True,
                    "placeholder": "输入云湖机器人 token"
                },
                {
                    "key": "base_url",
                    "label": "API 基地址",
                    "type": "string",
                    "default": "https://chat-go.jwzhd.com/open-apis/v1",
                    "required": True
                },
                {
                    "key": "websocket_url",
                    "label": "WebSocket 地址（可选）",
                    "type": "string",
                    "required": False,
                    "placeholder": "wss://ws.yhchat.com/v1",
                    "help": "如果云湖支持 WebSocket 事件流，可填写此地址，否则留空使用 webhook 接收消息"
                }
            ]
        }

    async def run(self, config: dict):
        """启动平台，由框架调用并传入配置"""
        self.config = config
        token = config.get('token', '')
        base_url = config.get('base_url', 'https://chat-go.jwzhd.com/open-apis/v1')
        ws_url = config.get('websocket_url', None)

        if not token:
            logger.error("云湖平台启动失败：未提供 token")
            return

        try:
            self.client = YunHuClient(token=token, base_url=base_url, websocket_url=ws_url)
            await self.client.start()
            self._running = True

            if ws_url:
                self.client.on('message', self._on_ws_message)
                self._ws_task = asyncio.create_task(self.client.start_event_stream())
                logger.info("云湖平台已启动（WebSocket模式）")
            else:
                logger.info("云湖平台已启动（仅HTTP发送，需配置webhook接收）")
        except Exception as e:
            logger.exception(f"云湖平台启动失败: {e}")

    async def stop(self):
        self._running = False
        if self._ws_task:
            self._ws_task.cancel()
        if self.client:
            await self.client.close()

    async def send_message(self, event: AstrMessageEvent):
        if not self.client:
            logger.warning("云湖客户端未初始化，无法发送消息")
            return

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

    async def _on_ws_message(self, event):
        logger.debug("收到 WebSocket 消息: %s", event)

    async def process_webhook(self, data: Dict[str, Any]):
        # webhook 处理逻辑（根据实际格式调整）
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