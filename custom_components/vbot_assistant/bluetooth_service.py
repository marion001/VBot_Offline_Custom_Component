"""Bluetooth management over the speaker's existing MQTT command channel."""
import asyncio
import json
import re
from uuid import uuid4

import voluptuous as vol
from homeassistant.components import mqtt
from homeassistant.const import ATTR_DEVICE_ID, ATTR_ENTITY_ID
from homeassistant.core import callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, DEVICE_TYPE_HOST
from .availability import is_vbot_device_online

ACTIONS = ('scan', 'pair', 'connect', 'sink_connect', 'device_disconnect')


async def async_bluetooth_command(hass, data, resolve):
    action, mac = data.get('action'), data.get('mac', '')
    if action not in ACTIONS:
        raise ServiceValidationError('Thao tác Bluetooth không hợp lệ')
    if action != 'scan' and (not isinstance(mac, str) or not re.fullmatch(r'(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', mac)):
        raise ServiceValidationError('Địa chỉ MAC không hợp lệ')
    devices = resolve(hass, data)
    if not devices:
        raise ServiceValidationError('Hãy chọn loa VBot')
    for device in devices:
        entries = hass.config_entries.async_entries(DOMAIN)
        if not any(getattr(getattr(entry, 'runtime_data', None), 'device_id', None) == device and
                   getattr(getattr(entry, 'runtime_data', None), 'device_type', None) == DEVICE_TYPE_HOST for entry in entries):
            raise ServiceValidationError('Thiết bị này không hỗ trợ quản lý Bluetooth')
        if not is_vbot_device_online(hass, device):
            raise ServiceValidationError('VBot đang ngoại tuyến')
    for device in devices:
        request_id = uuid4().hex
        future = asyncio.get_running_loop().create_future()
        @callback
        def received(message):
            try:
                result = json.loads(message.payload)
                if isinstance(result, dict) and result.get('request_id') == request_id and not future.done():
                    future.set_result(result)
            except (ValueError, TypeError):
                pass
        unsubscribe = await mqtt.async_subscribe(hass,
            f'{device}/script/bluetooth_output_control/state', received, qos=1)
        try:
            command = {'action': action, 'request_id': request_id}
            if action != 'scan':
                command['mac'] = mac.upper()
            await mqtt.async_publish(hass, f'{device}/script/bluetooth_output_control/set',
                                     json.dumps(command), qos=1, retain=False)
            result = await asyncio.wait_for(future, timeout=60)
            if result.get('success') is not True:
                raise ServiceValidationError(str(result.get('message') or 'Không thực hiện được thao tác Bluetooth'))
        except asyncio.TimeoutError as error:
            raise ServiceValidationError('Hết thời gian chờ Bluetooth. Kiểm tra VBot đã cập nhật và đang chạy.') from error
        finally:
            unsubscribe()
            if not future.done():
                future.cancel()


async def async_setup_bluetooth_service(hass, resolve):
    async def handle(call):
        await async_bluetooth_command(hass, call.data, resolve)
    if not hass.services.has_service(DOMAIN, 'bluetooth_command'):
        hass.services.async_register(DOMAIN, 'bluetooth_command', handle, schema=vol.Schema({
            vol.Optional(ATTR_DEVICE_ID): vol.Any(cv.string, [cv.string]),
            vol.Optional(ATTR_ENTITY_ID): vol.Any(cv.entity_id, [cv.entity_id]),
            vol.Required('action'): vol.In(ACTIONS),
            vol.Optional('mac', default=''): cv.string,
        }))
