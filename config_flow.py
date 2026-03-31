from astrbot.core import webui
from astrbot.core.webui import routes
from astrbot.core.webui.utils import render_template, json_response
from astrbot.core.webui.auth import requires_auth
from astrbot.core.plugin.manager import plugin_manager
import asyncio

@routes.route('/yunhu_adapter/config', methods=['GET', 'POST'])
@requires_auth
async def yunhu_adapter_config(request):
    """云湖适配器配置页面"""
    plugin = plugin_manager.get_plugin('yunhu_adapter')
    if not plugin:
        return render_template('error.html', message='插件未加载')

    if request.method == 'POST':
        data = await request.post()
        config = {
            'enabled': data.get('enabled') == 'on',
            'token': data.get('token', ''),
            'base_url': data.get('base_url', 'https://chat-go.jwzhd.com/open-apis/v1'),
            'websocket_url': data.get('websocket_url', '')
        }
        # 保存配置
        if hasattr(plugin, 'context') and hasattr(plugin.context, 'save_plugin_config'):
            await plugin.context.save_plugin_config('yunhu_adapter', config)
            logger.info("云湖适配器配置已保存")
        # 重载插件
        asyncio.create_task(plugin_manager.reload_plugin('yunhu_adapter'))
        return render_template('yunhu_adapter_config.html', saved=True, config=config)

    # GET 请求
    if hasattr(plugin, 'context') and hasattr(plugin.context, 'get_plugin_config'):
        config = plugin.context.get_plugin_config()
    else:
        config = {}
    return render_template('yunhu_adapter_config.html', config=config)

@routes.route('/yunhu/webhook', methods=['POST'])
async def yunhu_webhook(request):
    """云湖消息回调接收端点"""
    try:
        data = await request.json()
    except:
        data = await request.post()
    plugin = plugin_manager.get_plugin('yunhu_adapter')
    if plugin and plugin.platform:
        await plugin.platform.process_webhook(data)
    return json_response({"code": 0, "msg": "ok"})