"""Serve the bundled card and maintain its Lovelace resource."""
import logging
from pathlib import Path
from urllib.parse import urlsplit
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace import LOVELACE_DATA
from homeassistant.loader import async_get_integration

_LOGGER = logging.getLogger(__name__)
CARD_PATH = '/vbot_assistant/vbot-ultimate-card.js'


def _is_card_url(value):
    """Match only our local resource, leaving unrelated resources alone."""
    try:
        parts = urlsplit(str(value or ''))
        return not parts.scheme and not parts.netloc and parts.path == CARD_PATH
    except ValueError:
        return False


async def async_register_card_resource(hass, version):
    """Create/update one module resource without directly editing HA storage."""
    lovelace = hass.data.get(LOVELACE_DATA)
    resources = getattr(lovelace, 'resources', None)
    url = f'{CARD_PATH}?v={version}'
    if resources is None:
        _LOGGER.warning('Lovelace chưa sẵn sàng; thêm JavaScript module thủ công: %s', url)
        return
    # YAML resources are user owned. Do not rewrite their configuration file.
    if getattr(lovelace, 'resource_mode', None) == 'yaml':
        if not any(item.get('url') == url and item.get('type') == 'module'
                   for item in resources.async_items()):
            _LOGGER.warning('Lovelace dùng tài nguyên YAML; khai báo type: module, url: %s', url)
        return
    await resources.async_get_info()  # Load storage before checking for duplicates.
    matches = [item for item in resources.async_items() if _is_card_url(item.get('url'))]
    if not matches:
        await resources.async_create_item({'url': url, 'res_type': 'module'})
        return
    first = matches[0]
    if first.get('url') != url or first.get('type') != 'module':
        await resources.async_update_item(first['id'], {'url': url, 'res_type': 'module'})
    for duplicate in matches[1:]:
        await resources.async_delete_item(duplicate['id'])


async def async_setup_frontend(hass):
    await hass.http.async_register_static_paths([
        StaticPathConfig(CARD_PATH,
                         str(Path(__file__).parent/'www/vbot-ultimate-card.js'),False)
    ])
    try:
        integration = await async_get_integration(hass, 'vbot_assistant')
        await async_register_card_resource(hass, integration.version)
    except Exception:  # Frontend registration must not disable speaker controls.
        _LOGGER.exception('Không tự đăng ký được thẻ VBot; có thể thêm URL trong Resources thủ công')
