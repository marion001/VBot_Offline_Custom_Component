'''
Code By: Vũ Tuyển
GitHub VBot: https://github.com/marion001/VBot_Offline.git
Facebook Group: https://www.facebook.com/groups/1148385343358824
Facebook: https://www.facebook.com/TWFyaW9uMDAx
Mail: VBot.Assistant@gmail.com
'''

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.components import conversation, persistent_notification
from homeassistant.components import mqtt
from homeassistant.const import ATTR_DEVICE_ID, ATTR_ENTITY_ID
from homeassistant.exceptions import ConfigEntryError, ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from .const import (
    DOMAIN, TTS_DOMAIN, CONF_DEVICE_ID, VBot_URL_API, CONF_API_KEY,
    CONF_DEVICE_TYPE, CONF_AUTO_UPDATE_URL, CONF_URL_SOURCE, CONF_MDNS_LAST_UPDATE,
    URL_SOURCE_MANUAL, URL_SOURCE_MDNS,
    DEVICE_TYPE_HOST, DEVICE_TYPE_ANDROID, DEVICE_TYPE_ESP32,
    normalize_vbot_url, platforms_for_device,
)
from .conversation_agent import VBotConversationAgent
from .runtime import build_runtime_data
from .events import async_setup_event_bridge
from .availability import (
    async_setup_vbot_availability,
    async_unload_vbot_availability,
    reset_vbot_device_availability,
)
from .media_compat import async_check_media_api_compatibility
from .repairs import create_duplicate_device_issue, delete_duplicate_device_issue

_LOADED_DEVICE_IDS = "loaded_device_ids"


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
    if entry.version > 4:
        return False
    if entry.version == 4:
        return True

    data = dict(entry.data)
    options = dict(entry.options)
    last_mdns_update = options.get(
        CONF_MDNS_LAST_UPDATE,
        data.get(CONF_MDNS_LAST_UPDATE),
    )
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
    })
    data.pop(CONF_AUTO_UPDATE_URL, None)
    data.pop(CONF_URL_SOURCE, None)
    data.pop(CONF_MDNS_LAST_UPDATE, None)
    options.pop(VBot_URL_API, None)
    options.pop(CONF_API_KEY, None)
    options.update({
        CONF_AUTO_UPDATE_URL: auto_update,
        CONF_URL_SOURCE: source,
    })
    if last_mdns_update:
        options[CONF_MDNS_LAST_UPDATE] = last_mdns_update
    hass.config_entries.async_update_entry(
        entry,
        data=data,
        options=options,
        version=4,
    )
    return True

#Gọi khi người dùng thêm 1 cấu hình integration
async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    entry.runtime_data = build_runtime_data(hass, entry)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    runtime = entry.runtime_data
    canonical_device_id = runtime.device_id.casefold()
    loaded_device_ids = hass.data[DOMAIN].setdefault(_LOADED_DEVICE_IDS, {})
    conflicting_entry_id = loaded_device_ids.get(canonical_device_id)
    if conflicting_entry_id and conflicting_entry_id != entry.entry_id:
        conflicting_entry = hass.config_entries.async_get_entry(
            conflicting_entry_id
        )
        conflicting_title = (
            conflicting_entry.title if conflicting_entry else conflicting_entry_id
        )
        persistent_notification.async_create(
            hass,
            title="Trùng MQTT Client ID của VBot",
            message=(
                f"Không thể nạp **{entry.title}** vì MQTT Client ID "
                f"`{runtime.device_id}` trùng với **{conflicting_title}** khi "
                "so sánh không phân biệt chữ hoa/chữ thường. Hãy đổi Client ID "
                "trên một thiết bị rồi cấu hình lại entry bị lỗi."
            ),
            notification_id=f"vbot_duplicate_device_id_{canonical_device_id}",
        )
        create_duplicate_device_issue(
            hass, runtime.device_id, conflicting_title
        )
        raise ConfigEntryError(
            f"Duplicate VBot MQTT Client ID: {runtime.device_id}"
        )
    loaded_device_ids[canonical_device_id] = entry.entry_id
    delete_duplicate_device_issue(hass, runtime.device_id)
    reset_vbot_device_availability(hass, runtime.device_id)
    try:
        runtime.availability_coordinator = await async_setup_vbot_availability(
            hass, runtime.device_id, runtime
        )
    except Exception:
        loaded_device_ids.pop(canonical_device_id, None)
        raise
    agent_registered = False
    try:
        if runtime.device_id and runtime.device_type == DEVICE_TYPE_HOST:
            await async_setup_event_bridge(hass, entry)
            agent = VBotConversationAgent(hass, entry, runtime)
            conversation.async_set_agent(hass, entry, agent)
            agent_registered = True
        await hass.config_entries.async_forward_entry_setups(
            entry, platforms_for_device({CONF_DEVICE_TYPE: runtime.device_type})
        )
    except Exception:
        if agent_registered:
            conversation.async_unset_agent(hass, entry)
        await async_unload_vbot_availability(hass, runtime.device_id)
        reset_vbot_device_availability(hass, runtime.device_id)
        loaded_device_ids.pop(canonical_device_id, None)
        raise
    if runtime.device_type == DEVICE_TYPE_HOST:
        def schedule_media_compatibility_check() -> None:
            entry.async_create_background_task(
                hass,
                async_check_media_api_compatibility(hass, runtime),
                f"Kiểm tra Media API {runtime.device_id}",
            )

        entry.async_on_unload(
            runtime.availability_coordinator.async_add_online_listener(
                schedule_media_compatibility_check
            )
        )
        entry.async_create_background_task(
            hass,
            async_check_media_api_compatibility(hass, runtime),
            f"Kiểm tra Media API {runtime.device_id}",
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
    await async_unload_vbot_availability(hass, runtime.device_id)
    if runtime.device_type == DEVICE_TYPE_HOST:
        conversation.async_unset_agent(hass, entry)
    reset_vbot_device_availability(hass, runtime.device_id)
    loaded_device_ids = hass.data.get(DOMAIN, {}).get(_LOADED_DEVICE_IDS, {})
    if loaded_device_ids.get(runtime.device_id.casefold()) == entry.entry_id:
        loaded_device_ids.pop(runtime.device_id.casefold(), None)
    return True
