from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from .platform import YunHuPlatform

@register(
    name="yunhu_adapter",
    author="星落云",
    desc="云湖IM平台适配器",
    version="v1.0.6",
    repo="https://github.com/qdie1546-source/astrbot_plugin_yunhu_adapter"
)
class YunHuAdapter(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 创建平台实例（不启动，等待用户配置后由 AstrBot 调用 run）
        self.platform = YunHuPlatform(context)

    async def initialize(self):
        # 注册平台到 AstrBot 的平台管理器
        await self.context.platform_manager.register_platform(self.platform)
        logger.info("云湖适配器已注册，请在 WebUI 平台管理中配置并启用")

    async def terminate(self):
        await self.context.platform_manager.unregister_platform(self.platform)
        await self.platform.stop()