from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from .platform import YunHuPlatform

@register(
    name="yunhu_adapter",
    author="星落云",
    desc="云湖IM平台适配器",
    version="1.0.8",
    repo="https://github.com/qdie1546-source/astrbot_plugin_yunhu_adapter"
)
class YunHuAdapter(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        # 注册平台类，由框架负责实例化并传入正确的参数
        await self.context.platform_manager.register_platform(YunHuPlatform)
        logger.info("云湖适配器已注册，请在 WebUI 平台管理中配置并启用")

    async def terminate(self):
        pass