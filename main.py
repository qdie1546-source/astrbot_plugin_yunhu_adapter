from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from .platform import YunHuPlatform

@register(
    name="yunhu_adapter",
    author="星落云",
    desc="云湖IM平台适配器（使用token查询参数）",
    version="1.0.0",
    repo="https://github.com/qdie1546-source/astrbot_plugin_yunhu_adapter"
)
class YunHuAdapter(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.platform = None

    async def initialize(self):
        # 获取配置（AstrBot 4.22.0 使用 context.get_plugin_config）
        config = self.context.get_plugin_config() or {}
        enabled = config.get('enabled', False)
        if not enabled:
            logger.info("云湖适配器未启用")
            return

        token = config.get('token', '')
        base_url = config.get('base_url', 'https://chat-go.jwzhd.com/open-apis/v1')
        ws_url = config.get('websocket_url', None)  # 可选

        if not token:
            logger.error("云湖适配器已启用但未提供 token，请配置")
            return

        try:
            self.platform = YunHuPlatform(
                context=self.context,
                token=token,
                base_url=base_url,
                ws_url=ws_url
            )
            await self.context.platform_manager.register_platform(self.platform)
            logger.info("云湖适配器加载成功")
        except Exception as e:
            logger.exception(f"云湖适配器加载失败: {e}")

    async def terminate(self):
        if self.platform:
            await self.platform.stop()
            await self.context.platform_manager.unregister_platform(self.platform)