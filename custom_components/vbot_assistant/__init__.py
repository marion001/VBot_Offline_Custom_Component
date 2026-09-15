'''
Code By: Vũ Tuyển
GitHub VBot: https://github.com/marion001/VBot_Offline.git
Facebook Group: https://www.facebook.com/groups/1148385343358824
Facebook: https://www.facebook.com/TWFyaW9uMDAx
Mail: VBot.Assistant@gmail.com
'''

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.components import conversation
from homeassistant.components import mqtt
from homeassistant.const import ATTR_DEVICE_ID, ATTR_ENTITY_ID
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from .const import (
    DOMAIN, TTS_DOMAIN, CONF_DEVICE_ID, VBot_URL_API, CONF_API_KEY,
    CONF_DEVICE_TYPE, CONF_AUTO_UPDATE_URL, CONF_URL_SOURCE,
    URL_SOURCE_MANUAL, URL_SOURCE_MDNS,
    DEVICE_TYPE_HOST, DEVICE_TYPE_ANDROID, DEVICE_TYPE_ESP32,
    normalize_vbot_url, platforms_for_device,
)
from .conversation_agent import VBotConversationAgent
from .runtime import build_runtime_data
from .events import async_setup_event_bridge


def _as_list(value):
    """Normalize a service target field to a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _resolve_tts_devices(hass: HomeAssistant, call_data: dict) -> list[str]:
    """Resolve HA devices/entities and legacy MQTT client IDs."""
    configured = {}
    for entry in hass.config_entries.async_entries(DOMAIN):
        device_id = str(entry.data.get(CONF_DEVICE_ID, "")).strip()
        if device_id:
            configured[device_id.lower()] = device_id

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    resolved = []

    for value in _as_list(call_data.get(ATTR_DEVICE_ID)):
        target = str(value or "").strip()
        if not target:
            continue
        device = device_registry.async_get(target, include_child_devices=False)
        if device:
            identifiers = [
                identifier for domain, identifier in device.identifiers
                if domain == DOMAIN
            ]
            if not identifiers:
                raise ServiceValidationError(
                    f"Thiết bị {target} không thuộc VBot Assistant"
                )
            resolved.extend(identifiers)
            continue
        legacy = configured.get(target.lower())
        if not legacy:
            raise ServiceValidationError(
                f"Không tìm thấy VBot hoặc MQTT client ID: {target}"
            )
        resolved.append(legacy)

    for value in _as_list(call_data.get(ATTR_ENTITY_ID)):
        entity_id = str(value or "").strip()
        registry_entry = entity_registry.async_get(entity_id)
        if not registry_entry or registry_entry.platform != DOMAIN:
            raise ServiceValidationError(
                f"Entity {entity_id} không thuộc VBot Assistant"
            )
        if registry_entry.device_id:
            device = device_registry.async_get(
                registry_entry.device_id, include_child_devices=False
            )
            identifiers = (
                [identifier for domain, identifier in device.identifiers if domain == DOMAIN]
                if device else []
            )
            resolved.extend(identifiers)

    return list(dict.fromkeys(
        configured[value.lower()]
        for value in resolved
        if value.lower() in configured
    ))

#Hàm khởi tạo chung, không làm gì nếu không dùng YAML
async def async_setup(hass: HomeAssistant, config: dict):
    async def handle_tts(call):
        message = str(call.data.get("message", call.data.get("text", ""))).strip()
        if not message:
            raise ServiceValidationError("Nội dung TTS không được để trống")
        device_ids = _resolve_tts_devices(hass, call.data)
        if not device_ids:
            raise ServiceValidationError("Hãy chọn ít nhất một thiết bị VBot")
        for device_id in device_ids:
            await mqtt.async_publish(
                hass,
                f"{device_id}/script/vbot_tts/set",
                message,
                qos=1,
                retain=False,
            )

    if not hass.services.has_service(TTS_DOMAIN, "say"):
        hass.services.async_register(
            TTS_DOMAIN,
            "say",
            handle_tts,
            schema=vol.Schema({
                vol.Optional(ATTR_DEVICE_ID): vol.Any(cv.string, [cv.string]),
                vol.Optional(ATTR_ENTITY_ID): vol.Any(cv.entity_id, [cv.entity_id]),
                vol.Exclusive("message", "content"): cv.string,
                vol.Exclusive("text", "content"): cv.string,
            }),
        )
    return True


async def async_migrate_entry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Migrate legacy entries without changing their identity or entities."""
    if entry.version > 3:
        return False
    if entry.version == 3:
        return True

    data = dict(entry.data)
    options = dict(entry.options)
    device_type = data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_HOST)
    if device_type not in (
        DEVICE_TYPE_HOST,
        DEVICE_TYPE_ANDROID,
        DEVICE_TYPE_ESP32,
    ):
        device_type = DEVICE_TYPE_HOST
    raw_url = options.get(VBot_URL_API, data.get(VBot_URL_API, ""))
    normalized_url = normalize_vbot_url(raw_url, device_type)

    # Legacy entries are intentionally treated as manual so an mDNS
    # advertisement cannot unexpectedly replace a user-configured address.
    source = options.get(
        CONF_URL_SOURCE,
        data.get(CONF_URL_SOURCE, URL_SOURCE_MANUAL),
    )
    if source not in (URL_SOURCE_MANUAL, URL_SOURCE_MDNS):
        source = URL_SOURCE_MANUAL
    auto_update = bool(
        options.get(
            CONF_AUTO_UPDATE_URL,
            data.get(CONF_AUTO_UPDATE_URL, source == URL_SOURCE_MDNS),
        )
    )
    source = URL_SOURCE_MDNS if auto_update else URL_SOURCE_MANUAL

    data.update({
        CONF_DEVICE_TYPE: device_type,
        VBot_URL_API: normalized_url,
        CONF_API_KEY: str(
            options.get(CONF_API_KEY, data.get(CONF_API_KEY, ""))
        ).strip(),
        CONF_AUTO_UPDATE_URL: auto_update,
        CONF_URL_SOURCE: source,
    })
    options.update({
        VBot_URL_API: normalized_url,
        CONF_API_KEY: str(
            options.get(CONF_API_KEY, data.get(CONF_API_KEY, ""))
        ).strip(),
        CONF_AUTO_UPDATE_URL: auto_update,
        CONF_URL_SOURCE: source,
    })
    hass.config_entries.async_update_entry(
        entry,
        data=data,
        options=options,
        version=3,
    )
    return True

#Gọi khi người dùng thêm 1 cấu hình integration
async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    entry.runtime_data = build_runtime_data(hass, entry)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    runtime = entry.runtime_data
    if runtime.device_id and runtime.device_type == DEVICE_TYPE_HOST:
        await async_setup_event_bridge(hass, entry)
        agent = VBotConversationAgent(hass, entry, runtime)
        conversation.async_set_agent(hass, entry, agent)
    await hass.config_entries.async_forward_entry_setups(
        entry, platforms_for_device({CONF_DEVICE_TYPE: runtime.device_type})
    )
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """Nạp lại agent khi URL API trong Options thay đổi."""
    await hass.config_entries.async_reload(entry.entry_id)

#Gỡ bỏ khi người dùng xóa cấu hình
async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    runtime = entry.runtime_data
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, platforms_for_device({CONF_DEVICE_TYPE: runtime.device_type})
    )
    if not unload_ok:
        return False
    if runtime.device_type == DEVICE_TYPE_HOST:
        conversation.async_unset_agent(hass, entry)
    return True
