import asyncio
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register(
    name="yunhu_test",
    author="星落云",
    desc="云湖SDK测试插件，验证云湖IM接口连通性",
    version="1.0.2",
    repo="https://github.com/qdie1546-source/astrbot_plugin_yunhu_test"
)
class YunhuTestPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.config = context.get_plugin_config()
        self.client = None

    async def initialize(self):
        try:
            from yunhu import YunHuClient
            self.client = YunHuClient(
                token=self.config.get("token", ""),
                base_url=self.config.get("base_url", "https://api.yhchat.com/v1"),
                websocket_url=self.config.get("websocket_url", "wss://ws.yhchat.com/v1")
            )
            await self.client.start()
            logger.info("云湖 SDK 初始化成功")
        except Exception as e:
            logger.error(f"云湖 SDK 初始化失败: {e}")
            self.client = None

    @filter.command("yunhu_test")
    async def test_send(self, event: AstrMessageEvent):
        parts = event.message_str.strip().split(maxsplit=2)
        if len(parts) < 3:
            yield event.plain_result("用法: /yunhu_test <目标ID> <消息内容>")
            return
        target_id = parts[1]
        text = parts[2]
        if self.client is None:
            yield event.plain_result("SDK 未初始化，请检查插件配置中的 token")
            return
        try:
            from yunhu import TextMessage
            resp = await self.client.send_message(chat_id=target_id, message=TextMessage(text=text))
            yield event.plain_result(f"✅ 消息已发送，响应: {resp}")
        except Exception as e:
            logger.exception("发送消息失败")
            yield event.plain_result(f"❌ 发送失败: {e}")

    async def terminate(self):
        if self.client:
            await self.client.close()