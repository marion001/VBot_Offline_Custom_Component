'''
Code By: Vũ Tuyển
GitHub VBot: https://github.com/marion001/VBot_Offline.git
Facebook Group: https://www.facebook.com/groups/1148385343358824
Facebook: https://www.facebook.com/TWFyaW9uMDAx
Mail: VBot.Assistant@gmail.com
'''

import logging
import voluptuous as vol
from datetime import timedelta, datetime
from dataclasses import dataclass

from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.event import async_call_later
from .const import DOMAIN, DEVICE_TYPE_ANDROID, DEVICE_TYPE_ESP32, DEVICE_TYPE_HOST
from .availability import MQTTAvailabilityMixin
from .update_service import async_check_device_updates

_LOGGER = logging.getLogger(__name__)

#Thời gian mỗi lần kiểm tra cập nhật VBot mới (Phút)
VBOT_UPDATE_INTERVAL_MINUTES = 720 #720 = 12 tiếng


@dataclass(frozen=True, kw_only=True)
class VBotSwitchEntityDescription(SwitchEntityDescription):
    """Describe one MQTT-backed VBot switch."""

    state_topic: str
    command_topic: str
    payload_on: str = "ON"
    payload_off: str = "OFF"
    state_on: str = "ON"
    state_off: str = "OFF"
    optimistic: bool = False
    qos: int = 1
    retain: bool = True


def _switch_description(config: dict) -> VBotSwitchEntityDescription:
    """Convert legacy switch configuration without changing its identity."""
    state_topic = config["state_topic"]
    return VBotSwitchEntityDescription(
        key=state_topic,
        name=config["name"],
        icon=config.get("icon", "mdi:dip-switch"),
        state_topic=state_topic,
        command_topic=config["command_topic"],
        payload_on=config["payload_on"],
        payload_off=config["payload_off"],
        state_on=config["state_on"],
        state_off=config["state_off"],
        optimistic=config["optimistic"],
        qos=config["qos"],
        retain=config["retain"],
    )

class MQTTSwitch(MQTTAvailabilityMixin, SwitchEntity):
    def __init__(self, hass, device, description: VBotSwitchEntityDescription):
        self._hass = hass
        self._device = device
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{device.lower()}_{description.state_topic.replace('/', '_')}_switch"
        self._attr_device_class = "switch"
        self._attr_icon = description.icon
        self._state_topic = description.state_topic
        self._command_topic = description.command_topic
        self._payload_on = description.payload_on
        self._payload_off = description.payload_off
        self._state_on = description.state_on
        self._state_off = description.state_off
        self._optimistic = description.optimistic
        self._qos = description.qos
        self._is_on = False
        self._legacy_retained_command_cleared = False

    async def _async_clear_legacy_retained_command(self):
        """Xóa retained command cũ một lần trước lệnh mới đầu tiên."""
        if self._legacy_retained_command_cleared:
            return
        await mqtt.async_publish(
            self._hass,
            self._command_topic,
            "",
            self._qos,
            True,
        )
        self._legacy_retained_command_cleared = True

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        unsubscribe = await mqtt.async_subscribe(
            self._hass, self._state_topic, self._message_received, self._qos
        )
        self.async_on_remove(unsubscribe)

    @property
    def is_on(self):
        return self._is_on

    async def async_turn_on(self, **kwargs):
        # Command topic không được retain, nếu không broker sẽ phát lại lệnh
        # cũ mỗi khi VBot kết nối lại.
        await self._async_clear_legacy_retained_command()
        await mqtt.async_publish(
            self._hass,
            self._command_topic,
            self._payload_on,
            self._qos,
            False,
        )
        if self._optimistic:
            self._is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self._async_clear_legacy_retained_command()
        await mqtt.async_publish(
            self._hass,
            self._command_topic,
            self._payload_off,
            self._qos,
            False,
        )
        if self._optimistic:
            self._is_on = False
            self.async_write_ha_state()

    async def _message_received(self, msg):
        payload = msg.payload
        #_LOGGER.debug(f"{self._name} MQTT nhận: {payload}")
        self._is_on = payload == self._state_on
        self.async_write_ha_state()

#Switch kiểm tra cập nhật RIÊNG cho TỪNG thiết bị Client
class VBotCheckAllUpdatesSwitch(MQTTAvailabilityMixin, SwitchEntity, RestoreEntity):
    def __init__(self, hass, entry_id, device_id):
        self.hass = hass
        self._entry_id = entry_id
        self._device_id = device_id
        self._device = device_id
        self._attr_name = f"Tự động kiểm tra cập nhật VBot ({device_id})"
        self._attr_unique_id = f"{device_id}_check_all_updates"
        self._attr_icon = "mdi:progress-upload"
        self._is_on = True
        self._cancel_update_timer = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._is_on = last_state.state == "on"
        if self._is_on:
            await self._start_device_task()

    async def async_will_remove_from_hass(self):
        """Stop the per-entry timer before a reload or unload."""
        await self._stop_device_task()
        await super().async_will_remove_from_hass()

    @property
    def is_on(self):
        return self._is_on

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"VBot Assistant Updates {self._device_id}",
            "manufacturer": "Vũ Tuyển",
            "model": "VBot Assistant Custom Component"
        }

    @property
    def extra_state_attributes(self):
        return {
            "last_check": "N/A",
            "auto_check_enabled": self._cancel_update_timer is not None,
            "next_check": f"{VBOT_UPDATE_INTERVAL_MINUTES} minutes",
            "device_id": self._device_id
        }

    async def async_turn_on(self, **kwargs):
        self._is_on = True
        self.async_write_ha_state()
        await self._start_device_task()
        await async_check_device_updates(
            self.hass, self._device_id, entry_id=self._entry_id
        )

    async def async_turn_off(self, **kwargs):
        self._is_on = False
        self.async_write_ha_state()
        await self._stop_device_task()

    #Khởi động task RIÊNG cho thiết bị này
    async def _start_device_task(self):
        if self._cancel_update_timer is not None:
            await self._stop_device_task()
        interval = timedelta(minutes=VBOT_UPDATE_INTERVAL_MINUTES)
        async def device_task(_now):
            try:
                await async_check_device_updates(
                    self.hass, self._device_id, entry_id=self._entry_id
                )
            except Exception as e:
                _LOGGER.error(f"[VBot] Lỗi auto check {self._device_id}: {e}")
        self._cancel_update_timer = async_track_time_interval(
            self.hass, device_task, interval
        )

    #Dừng task RIÊNG của thiết bị này
    async def _stop_device_task(self):
        if self._cancel_update_timer is not None:
            self._cancel_update_timer()
            self._cancel_update_timer = None

# Compatibility wrapper retained for existing custom imports.
async def check_single_device_updates(
    hass, device_id, entry_id=None, notify_when_current=False
):
    return await async_check_device_updates(
        hass,
        device_id,
        entry_id=entry_id,
        notify_when_current=notify_when_current,
    )

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    _LOGGER.error("VBot Assistant MQTT không hỗ trợ cấu hình YAML. Vui lòng dùng UI (config_entry).")
    pass

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    hass.data.setdefault(DOMAIN, {})
    runtime = entry.runtime_data
    device = runtime.device_id
    if not device:
        _LOGGER.error("[VBot Assistant MQTT] Không tìm thấy Tên Client trong mục cấu hình")
        return
    switches = [
          {
            "name": f"Logs Hệ Thống Active ({device})",
            "state_topic": f"{device}/switch/log_display_active/state",
            "command_topic": f"{device}/switch/log_display_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:math-log"
          },
          {
            "name": f"Chế Độ Hội Thoại Active ({device})",
            "state_topic": f"{device}/switch/conversation_mode/state",
            "command_topic": f"{device}/switch/conversation_mode/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:repeat-once"
          },
          {
            "name": f"Chế Độ Câu Phản Hồi Active ({device})",
            "state_topic": f"{device}/switch/wakeup_reply/state",
            "command_topic": f"{device}/switch/wakeup_reply/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:reply-all"
          },
          {
            "name": f"Mic, Microphone Active ({device})",
            "state_topic": f"{device}/switch/mic_on_off/state",
            "command_topic": f"{device}/switch/mic_on_off/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:microphone-settings"
          },
          {
            "name": f"Media Player Active ({device})",
            "state_topic": f"{device}/switch/media_player_active/state",
            "command_topic": f"{device}/switch/media_player_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:multimedia"
          },
          {
            "name": f"Wakeup Hotword in Media Player Active ({device})",
            "state_topic": f"{device}/switch/wake_up_in_media_player/state",
            "command_topic": f"{device}/switch/wake_up_in_media_player/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:speaker-play"
          },
          {
            "name": f"Cache TTS Active ({device})",
            "state_topic": f"{device}/switch/cache_tts_active/state",
            "command_topic": f"{device}/switch/cache_tts_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:cached"
          },
          {
            "name": f"Wake UP ({device})",
            "state_topic": f"{device}/switch/conversation_mode_flag/state",
            "command_topic": f"{device}/switch/conversation_mode_flag/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:play-circle-outline"
          },
          {
            "name": f"Home Asistant Active ({device})",
            "state_topic": f"{device}/switch/home_assistant_active/state",
            "command_topic": f"{device}/switch/home_assistant_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:home-assistant"
          },
          {
            "name": f"Home Asistant Custom Command Active ({device})",
            "state_topic": f"{device}/switch/hass_custom_commands_active/state",
            "command_topic": f"{device}/switch/hass_custom_commands_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:home-plus"
          },
          {
            "name": f"DEV Custom Active ({device})",
            "state_topic": f"{device}/switch/developer_customization/state",
            "command_topic": f"{device}/switch/developer_customization/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:dev-to"
          },
          {
            "name": f"Xử Lý Tiếp Cho DEV Skill Active ({device})",
            "state_topic": f"{device}/switch/dev_vbot_processing_active/state",
            "command_topic": f"{device}/switch/dev_vbot_processing_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:developer-board"
          },
          {
            "name": f"Default Assistant Active ({device})",
            "state_topic": f"{device}/switch/default_assistant_active/state",
            "command_topic": f"{device}/switch/default_assistant_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:assistant"
          },
          {
            "name": f"Dify AI Active ({device})",
            "state_topic": f"{device}/switch/dify_ai_active/state",
            "command_topic": f"{device}/switch/dify_ai_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:assistant"
          },
          {
            "name": f"Google Gemini Active ({device})",
            "state_topic": f"{device}/switch/google_gemini_active/state",
            "command_topic": f"{device}/switch/google_gemini_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:google-assistant"
          },
          {
            "name": f"Chat GPT Active ({device})",
            "state_topic": f"{device}/switch/chat_gpt_active/state",
            "command_topic": f"{device}/switch/chat_gpt_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:assistant"
          },
          {
            "name": f"Music Local Active ({device})",
            "state_topic": f"{device}/switch/music_local_active/state",
            "command_topic": f"{device}/switch/music_local_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:music-circle-outline"
          },
          {
            "name": f"ZingMp3 Active ({device})",
            "state_topic": f"{device}/switch/zing_mp3_active/state",
            "command_topic": f"{device}/switch/zing_mp3_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:music-circle"
          },
          {
            "name": f"Youtube Active ({device})",
            "state_topic": f"{device}/switch/youtube_active/state",
            "command_topic": f"{device}/switch/youtube_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:youtube"
          },
          {
            "name": f"Logs MQTT Broker Active ({device})",
            "state_topic": f"{device}/switch/mqtt_show_logs_reconnect/state",
            "command_topic": f"{device}/switch/mqtt_show_logs_reconnect/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:math-log"
          },
          {
            "name": f"News Paper Active ({device})",
            "state_topic": f"{device}/switch/news_paper_active/state",
            "command_topic": f"{device}/switch/news_paper_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:podcast"
          },
          {
            "name": f"Radio Active ({device})",
            "state_topic": f"{device}/switch/radio_active/state",
            "command_topic": f"{device}/switch/radio_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:radio"
          },
          {
            "name": f"PodCast Active ({device})",
            "state_topic": f"{device}/switch/podcast_active/state",
            "command_topic": f"{device}/switch/podcast_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:radio-tower"
          },
          {
            "name": f"Zalo AI Assistant Active ({device})",
            "state_topic": f"{device}/switch/zalo_assistant_active/state",
            "command_topic": f"{device}/switch/zalo_assistant_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:assistant"
          },
          {
            "name": f"Multiple Command Active ({device})",
            "state_topic": f"{device}/switch/multiple_command_active/state",
            "command_topic": f"{device}/switch/multiple_command_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:apple-keyboard-command"
          },
          {
            "name": f"Continue Listening After Commands Active ({device})",
            "state_topic": f"{device}/switch/continue_listening_after_commands/state",
            "command_topic": f"{device}/switch/continue_listening_after_commands/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:chevron-double-up"
          },
          {
            "name": f"Olli AI Assistant Active ({device})",
            "state_topic": f"{device}/switch/olli_assistant_active/state",
            "command_topic": f"{device}/switch/olli_assistant_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:assistant"
          },
          {
            "name": f"XiaoZhi AI Active ({device})",
            "state_topic": f"{device}/switch/xiaozhi_active/state",
            "command_topic": f"{device}/switch/xiaozhi_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:assistant"
          },
          {
            "name": f"DEV Custom Assistant Active ({device})",
            "state_topic": f"{device}/switch/dev_custom_assistant_active/state",
            "command_topic": f"{device}/switch/dev_custom_assistant_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:assistant"
          },
          {
            "name": f"NhacCuaTui Active ({device})",
            "state_topic": f"{device}/switch/nhaccuatui_active/state",
            "command_topic": f"{device}/switch/nhaccuatui_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:music-circle"
          },
          {
            "name": f"Phát Lặp Lại Danh Sách Nhạc ({device})",
            "state_topic": f"{device}/switch/playlist_loop/state",
            "command_topic": f"{device}/switch/playlist_loop/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:repeat-variant"
          },
    ]
    if runtime.device_type == DEVICE_TYPE_ANDROID:
        supported = {
            "conversation_mode", "mic_on_off", "media_player_active",
            "wake_up_in_media_player", "playlist_loop",
        }
        switches = [
            item for item in switches
            if any(f"/switch/{name}/set" in item["command_topic"] for name in supported)
        ]
        switches.append({
            "name": f"Bluetooth Active ({device})",
            "state_topic": f"{device}/switch/bluetooth_active/state",
            "command_topic": f"{device}/switch/bluetooth_active/set",
            "payload_on": "ON", "payload_off": "OFF",
            "state_on": "ON", "state_off": "OFF",
            "optimistic": False, "qos": 1, "retain": True,
            "icon": "mdi:bluetooth",
        })
    elif runtime.device_type == DEVICE_TYPE_ESP32:
        supported = {"conversation_mode", "mic_on_off"}
        switches = [
            item for item in switches
            if any(f"/switch/{name}/set" in item["command_topic"] for name in supported)
        ]
        switches.append({
            "name": f"Hotword Stream ({device})",
            "state_topic": f"{device}/switch/hotword_stream/state",
            "command_topic": f"{device}/switch/hotword_stream/set",
            "payload_on": "ON", "payload_off": "OFF",
            "state_on": "ON", "state_off": "OFF",
            "optimistic": False, "qos": 1, "retain": True,
            "icon": "mdi:account-voice",
        })
        switches.append({
            "name": f"LED Active ({device})",
            "state_topic": f"{device}/switch/led_active/state",
            "command_topic": f"{device}/switch/led_active/set",
            "payload_on": "ON", "payload_off": "OFF",
            "state_on": "ON", "state_off": "OFF",
            "optimistic": False, "qos": 1, "retain": True,
            "icon": "mdi:led-strip-variant",
        })
    ents = [
        MQTTSwitch(hass, device, _switch_description(config))
        for config in switches
    ]
    if runtime.device_type == DEVICE_TYPE_HOST:
        ents.append(VBotCheckAllUpdatesSwitch(hass, entry.entry_id, device))
    async_add_entities(ents, update_before_add=True)
