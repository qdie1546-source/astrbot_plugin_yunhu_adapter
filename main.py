from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from .platform import YunHuPlatform

@register(
    name="yunhu_adapter",
    author="星落云",
    desc="云湖IM平台适配器",
    version="v1.0.5",
    repo="https://github.com/qdie1546-source/astrbot_plugin_yunhu_adapter"
)
class YunHuAdapter(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.platform = None

    async def initialize(self):
        """插件加载时，注册平台适配器（无需立即启动，等待用户配置）"""
        # 注册平台，AstrBot 会在 WebUI 中显示“云湖”平台供用户添加实例
        self.platform = YunHuPlatform(self.context)
        await self.context.platform_manager.register_platform(self.platform)
        logger.info("云湖适配器已注册，请在 WebUI 平台管理中配置并启用")

    async def terminate(self):
        if self.platform:
            await self.platform.stop()
            await self.context.platform_manager.unregister_platform(self.platform)