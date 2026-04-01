from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from .platform import YunHuPlatform

@register(
    name="yunhu_adapter",
    author="星落云",
    desc="云湖IM平台适配器",
    version="v1.0.9",
    repo="https://github.com/qdie1546-source/astrbot_plugin_yunhu_adapter"
)
class YunHuAdapter(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        # 尝试多种方法注册平台
        platform_manager = self.context.platform_manager
        try:
            # 尝试新方法名 add_platform
            if hasattr(platform_manager, 'add_platform'):
                await platform_manager.add_platform(YunHuPlatform)
                logger.info("云湖平台已通过 add_platform 注册")
            elif hasattr(platform_manager, 'register_platform'):
                await platform_manager.register_platform(YunHuPlatform)
                logger.info("云湖平台已通过 register_platform 注册")
            else:
                logger.error("PlatformManager 没有可用的注册方法，请检查 AstrBot 版本")
        except Exception as e:
            logger.exception(f"注册平台时出错: {e}")

    async def terminate(self):
        pass