import asyncio
from typing import Dict, Any, List, Union
from astrbot.api.platform import Platform, AstrMessageEvent, AstrBotMessage, MessageMember
from astrbot.api.message_components import Plain, Image, At
from astrbot.api import logger
from yunhu import YunHuClient
from yunhu.models import TextMessage, ImageMessage, AtMessage

class YunHuPlatform(Platform):
    def __init__(self, context):
        super().__init__(context)
        self.client = None
        self.config = {}  # 将在 run 时从平台配置中获取
        self._running = False
        self._ws_task = None

    async def run(self, config: Dict[str, Any]):
        """
        启动平台实例，由 AstrBot 在用户添加平台并启用后调用。
        config 包含用户在 WebUI 中填写的配置项。
        """
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

            # 如果有 WebSocket 事件流，则启动
            if ws_url:
                self.client.on('message', self._on_ws_message)
                self._ws_task = asyncio.create_task(self.client.start_event_stream())
                logger.info("云湖平台已启动（WebSocket模式）")
            else:
                logger.info("云湖平台已启动（仅HTTP发送，需配置webhook接收）")
        except Exception as e:
            logger.exception(f"云湖平台启动失败: {e}")

    async def stop(self):
        """停止平台实例"""
        self._running = False
        if self._ws_task:
            self._ws_task.cancel()
        if self.client:
            await self.client.close()

    async def send_message(self, event: AstrMessageEvent):
        """发送消息"""
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
        """AstrBot消息链转云湖消息"""
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

    # ========== WebSocket 事件处理 ==========
    async def _on_ws_message(self, event):
        """处理 WebSocket 接收到的消息"""
        # 将云湖消息转换为 AstrMessageEvent 并分发
        # 根据实际云湖事件格式编写
        pass

    # ========== Webhook 消息接收（由外部路由调用）==========
    async def process_webhook(self, data: Dict[str, Any]):
        """
        处理通过 HTTP webhook 推送的消息。
        此方法可由外部 HTTP 路由调用（如 /yunhu/webhook），
        您需要在 AstrBot 的 WebUI 中添加自定义路由或使用插件提供的端点。
        """
        # 根据实际推送格式解析，构造 AstrMessageEvent
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