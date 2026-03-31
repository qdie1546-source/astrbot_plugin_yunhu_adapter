import os
import json
import asyncio
from astrbot.core.webui import routes
from astrbot.core.webui.utils import render_template, json_response
from astrbot.core.webui.auth import requires_auth
from astrbot.core.plugin.manager import plugin_manager

@routes.route('/yunhu_adapter/config', methods=['GET', 'POST'])
@requires_auth
async def yunhu_adapter_config(request):
    plugin = plugin_manager.get_plugin('yunhu_adapter')
    if not plugin:
        return render_template('error.html', message='插件未加载')

    config_path = os.path.join(os.path.dirname(plugin.__file__), 'config.json')
    current_config = {}
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            current_config = json.load(f)

    if request.method == 'POST':
        data = await request.post()
        config = {
            'enabled': data.get('enabled') == 'on',
            'token': data.get('token', ''),
            'base_url': data.get('base_url', 'https://chat-go.jwzhd.com/open-apis/v1'),
            'websocket_url': data.get('websocket_url', '')
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        asyncio.create_task(plugin_manager.reload_plugin('yunhu_adapter'))
        return render_template('yunhu_adapter_config.html', saved=True, config=config)

    return render_template('yunhu_adapter_config.html', config=current_config)

@routes.route('/yunhu/webhook', methods=['POST'])
async def yunhu_webhook(request):
    try:
        data = await request.json()
    except:
        data = await request.post()
    plugin = plugin_manager.get_plugin('yunhu_adapter')
    if plugin and plugin.platform:
        await plugin.platform.process_webhook(data)
    return json_response({"code": 0, "msg": "ok"})