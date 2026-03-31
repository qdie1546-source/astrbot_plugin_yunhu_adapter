import os
import json
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from .platform import YunHuPlatform

@register(
    name="yunhu_adapter",
    author="星落云",
    desc="云湖IM平台适配器（使用token查询参数）",
    version="v1.0.4",
    repo="https://github.com/qdie1546-source/astrbot_plugin_yunhu_adapter"
)
class YunHuAdapter(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.platform = None
        self.config_path = os.path.join(os.path.dirname(__file__), 'config.json')

    def _get_config(self):
        """从 config.json 读取配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"读取配置文件失败: {e}")
        return {}

    async def initialize(self):
        config = self._get_config()
        enabled = config.get('enabled', False)
        if not enabled:
            logger.info("云湖适配器未启用")
            return

        token = config.get('token', '')
        base_url = config.get('base_url', 'https://chat-go.jwzhd.com/open-apis/v1')
        ws_url = config.get('websocket_url', None)

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