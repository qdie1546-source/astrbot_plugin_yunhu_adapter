import os
import json
import asyncio
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.message_components import Plain
from yunhu import YunHuClient
from aiohttp import web
import threading

PLUGIN_DIR = os.path.dirname(__file__)
CONFIG_FILE = os.path.join(PLUGIN_DIR, "config.json")
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>云湖适配器配置</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/mdui@1.0.2/dist/css/mdui.min.css"/>
    <script src="https://cdn.jsdelivr.net/npm/mdui@1.0.2/dist/js/mdui.min.js"></script>
</head>
<body class="mdui-container">
    <div class="mdui-typo">
        <h1>云湖适配器配置</h1>
        <form method="post" action="/config">
            <div class="mdui-textfield">
                <label class="mdui-textfield-label">启用适配器</label>
                <label class="mdui-switch">
                    <input type="checkbox" name="enabled" %s/>
                    <i class="mdui-switch-icon"></i>
                </label>
            </div>
            <div class="mdui-textfield">
                <label class="mdui-textfield-label">云湖 Token</label>
                <input class="mdui-textfield-input" type="text" name="token" value="%s"/>
            </div>
            <div class="mdui-textfield">
                <label class="mdui-textfield-label">API 基地址</label>
                <input class="mdui-textfield-input" type="text" name="base_url" value="%s"/>
                <div class="mdui-textfield-helper">默认: https://chat-go.jwzhd.com/open-apis/v1</div>
            </div>
            <div class="mdui-textfield">
                <label class="mdui-textfield-label">消息回调地址</label>
                <input class="mdui-textfield-input" type="text" readonly value="http://你的服务器IP:8876/webhook"/>
                <div class="mdui-textfield-helper">请将此地址填入云湖的消息订阅接口</div>
            </div>
            <button type="submit" class="mdui-btn mdui-btn-raised mdui-color-theme-accent">保存配置</button>
            %s
        </form>
    </div>
</body>
</html>
'''

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'enabled': False, 'token': '', 'base_url': 'https://chat-go.jwzhd.com/open-apis/v1'}

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

@register(
    name="yunhu_adapter",
    author="星落云",
    desc="云湖IM适配器（独立HTTP服务）",
    version="3.0.0",
    repo="https://github.com/qdie1546-source/astrbot_plugin_yunhu_adapter"
)
class YunHuAdapter(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.config = get_config()
        self.client = None
        self._http_server = None
        self._server_task = None

    async def initialize(self):
        # 初始化客户端
        await self._init_client()
        # 启动独立 HTTP 服务器（端口 8876）
        self._server_task = asyncio.create_task(self._run_http_server())
        logger.info("云湖适配器已启动（独立 HTTP 服务在端口 8876）")

    async def _init_client(self):
        if self.config.get('enabled') and self.config.get('token'):
            try:
                if self.client:
                    await self.client.close()
                self.client = YunHuClient(
                    token=self.config['token'],
                    base_url=self.config.get('base_url', 'https://chat-go.jwzhd.com/open-apis/v1')
                )
                await self.client.start()
                logger.info("云湖客户端已初始化")
            except Exception as e:
                logger.exception("初始化云湖客户端失败")
                self.client = None
        else:
            self.client = None

    async def _run_http_server(self):
        """启动 aiohttp 服务器"""
        app = web.Application()
        app.router.add_get('/', self.handle_config_page)
        app.router.add_post('/config', self.handle_config_save)
        app.router.add_post('/webhook', self.handle_webhook)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8876)
        await site.start()
        logger.info("云湖配置服务已启动: http://0.0.0.0:8876")
        # 保持运行
        await asyncio.Event().wait()

    async def handle_config_page(self, request):
        """显示配置页面"""
        config = get_config()
        enabled_checked = 'checked' if config.get('enabled') else ''
        token_val = config.get('token', '')
        base_url_val = config.get('base_url', 'https://chat-go.jwzhd.com/open-apis/v1')
        saved_msg = ''
        return web.Response(
            text=HTML_TEMPLATE % (enabled_checked, token_val, base_url_val, saved_msg),
            content_type='text/html'
        )

    async def handle_config_save(self, request):
        """保存配置"""
        data = await request.post()
        new_config = {
            'enabled': data.get('enabled') == 'on',
            'token': data.get('token', ''),
            'base_url': data.get('base_url', 'https://chat-go.jwzhd.com/open-apis/v1')
        }
        save_config(new_config)
        self.config = new_config
        # 重新初始化客户端
        await self._init_client()
        # 重新渲染页面，显示成功信息
        enabled_checked = 'checked' if new_config['enabled'] else ''
        token_val = new_config['token']
        base_url_val = new_config['base_url']
        saved_msg = '<div class="mdui-alert mdui-color-green mdui-m-t-2">配置已保存，插件已重载。</div>'
        return web.Response(
            text=HTML_TEMPLATE % (enabled_checked, token_val, base_url_val, saved_msg),
            content_type='text/html'
        )

    async def handle_webhook(self, request):
        """接收云湖推送的消息"""
        try:
            data = await request.json()
        except:
            data = await request.post()
        await self._process_webhook(data)
        return web.json_response({"code": 0, "msg": "ok"})

    async def _process_webhook(self, data: dict):
        """将云湖消息转换为 AstrBot 消息事件并分发"""
        try:
            msg_data = data.get('message', {})
            chat_id = msg_data.get('chat_id')
            text = msg_data.get('text')
            sender_id = msg_data.get('sender', {}).get('id')
            sender_name = msg_data.get('sender', {}).get('name')
            if not chat_id or not text:
                logger.debug("webhook消息缺少必要字段")
                return

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
                platform=None
            )
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
        if self._server_task:
            self._server_task.cancel()