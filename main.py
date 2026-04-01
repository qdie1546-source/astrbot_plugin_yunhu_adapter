import os
import json
import asyncio
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.webui import routes
from astrbot.core.webui.utils import json_response, render_template
from astrbot.core.plugin.manager import plugin_manager
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.message_components import Plain
from yunhu import YunHuClient

# 插件目录
PLUGIN_DIR = os.path.dirname(__file__)
CONFIG_FILE = os.path.join(PLUGIN_DIR, "config.json")

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

@register(
    name="yunhu_adapter",
    author="星落云",
    desc="云湖IM适配器（非平台模式）",
    version="v2.0.0",
    repo="https://github.com/qdie1546-source/astrbot_plugin_yunhu_adapter"
)
class YunHuAdapter(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.client = None
        self.config = get_config()
        self._running = False

    async def initialize(self):
        # 启动 HTTP 路由（配置页面和 webhook）
        self._register_routes()
        # 初始化客户端（如果有 token）
        await self._init_client()
        logger.info("云湖适配器已启动（非平台模式）")

    async def _init_client(self):
        token = self.config.get('token', '')
        base_url = self.config.get('base_url', 'https://chat-go.jwzhd.com/open-apis/v1')
        if token and not self.client:
            self.client = YunHuClient(token=token, base_url=base_url)
            await self.client.start()
            logger.info("云湖客户端已初始化")

    def _register_routes(self):
        """注册 HTTP 路由（配置页面 + webhook）"""
        from astrbot.core.webui import app

        @app.route('/yunhu/config', methods=['GET', 'POST'])
        async def yunhu_config(request):
            if request.method == 'POST':
                data = await request.post()
                new_config = {
                    'enabled': data.get('enabled') == 'on',
                    'token': data.get('token', ''),
                    'base_url': data.get('base_url', 'https://chat-go.jwzhd.com/open-apis/v1')
                }
                save_config(new_config)
                self.config = new_config
                # 重新初始化客户端
                if self.client:
                    await self.client.close()
                    self.client = None
                await self._init_client()
                return render_template('yunhu_config.html', saved=True, config=new_config)
            return render_template('yunhu_config.html', config=self.config)

        @app.route('/yunhu/webhook', methods=['POST'])
        async def yunhu_webhook(request):
            """接收云湖推送的消息"""
            try:
                data = await request.json()
            except:
                data = await request.post()
            # 处理消息
            await self._process_webhook(data)
            return json_response({"code": 0, "msg": "ok"})

    async def _process_webhook(self, data: dict):
        """将云湖消息转换为 AstrBot 消息事件并分发"""
        # 根据实际云湖推送格式调整
        try:
            msg_data = data.get('message', {})
            chat_id = msg_data.get('chat_id')
            text = msg_data.get('text')
            sender_id = msg_data.get('sender', {}).get('id')
            sender_name = msg_data.get('sender', {}).get('name')
            if not chat_id or not text:
                logger.debug("webhook消息缺少必要字段")
                return

            # 构造 AstrBot 消息对象
            from astrbot.api.platform import AstrMessageEvent, AstrBotMessage, MessageMember
            astr_msg = AstrBotMessage()
            astr_msg.type = "group" if chat_id != sender_id else "private"
            astr_msg.self_id = ""
            astr_msg.session_id = chat_id
            astr_msg.message_id = data.get('message_id', '')
            astr_msg.group_id = chat_id if astr_msg.type == "group" else ""
            astr_msg.sender = MessageMember(user_id=sender_id, nickname=sender_name)
            astr_msg.message = [Plain(text)]
            astr_msg.message_str = text
            astr_msg.timestamp = int(data.get('timestamp', 0))

            astr_event = AstrMessageEvent(
                platform_name="yunhu",
                message_obj=astr_msg,
                platform=None  # 非平台模式，platform 为 None
            )
            # 分发到 AstrBot 消息处理链
            await self.context.message_dispatcher.dispatch(astr_event)
        except Exception as e:
            logger.exception("处理 webhook 消息失败")

    @filter.command("yunhu_send")
    async def send_test(self, event: AstrMessageEvent, chat_id: str, *args):
        """测试发送消息：/yunhu_send 目标ID 消息内容"""
        text = ' '.join(args)
        if not text:
            yield event.plain_result("用法: /yunhu_send 目标ID 消息内容")
            return
        if not self.client:
            yield event.plain_result("云湖客户端未初始化，请检查配置")
            return
        try:
            resp = await self.client.send_message(chat_id, text)
            yield event.plain_result(f"✅ 发送成功: {resp}")
        except Exception as e:
            yield event.plain_result(f"❌ 发送失败: {e}")

    async def terminate(self):
        if self.client:
            await self.client.close()