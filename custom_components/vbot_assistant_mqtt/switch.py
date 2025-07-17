import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntity
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    _LOGGER.warning("VBot Assistant MQTT không hỗ trợ cấu hình YAML. Vui lòng dùng UI (config_entry).")
    pass

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    cfg = entry.data
    device = cfg.get(CONF_DEVICE_ID)
    if not device:
        _LOGGER.error("Không tìm thấy Tên Client trong mục cấu hình")
        return
    switches = [
          {
            "name": f"{device} Logs Hệ Thống Active",
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
            "name": f"{device} Chế Độ Hội Thoại Active",
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
            "name": f"{device} Chế Độ Câu Phản Hồi Active",
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
            "name": f"{device} Mic, Microphone Active",
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
            "name": f"{device} Media Player Active",
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
            "name": f"{device} Wakeup Hotword in Media Player Active",
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
            "name": f"{device} Cache TTS Active",
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
            "name": f"{device} Wake UP",
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
            "name": f"{device} Home Asistant Active",
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
            "name": f"{device} Home Asistant Custom Command Active",
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
            "name": f"{device} DEV Custom Active",
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
            "name": f"{device} Xử Lý Tiếp Cho DEV Skill Active",
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
            "name": f"{device} Default Assistant Active",
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
            "name": f"{device} Dify AI Active",
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
            "name": f"{device} Google Gemini Active",
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
            "name": f"{device} Chat GPT Active",
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
            "name": f"{device} Music Local Active",
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
            "name": f"{device} ZingMp3 Active",
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
            "name": f"{device} Youtube Active",
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
            "name": f"{device} Logs MQTT Broker Active",
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
            "name": f"{device} News Paper Active",
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
            "name": f"{device} Radio Active",
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
            "name": f"{device} PodCast Active",
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
            "name": f"{device} Zalo AI Assistant Active",
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
            "name": f"{device} Display Screen Active",
            "state_topic": f"{device}/switch/display_screen_active/state",
            "command_topic": f"{device}/switch/display_screen_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
            "icon": "mdi:monitor-shimmer"
          },
          {
            "name": f"{device} Multiple Command Active",
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
            "name": f"{device} Continue Listening After Commands Active",
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
            "name": f"{device} Olli AI Assistant Active",
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
            "name": f"{device} DEV Custom Assistant Active",
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
    ]
    #ents = [MQTTSwitch(hass, **s) for s in switches]
    ents = [MQTTSwitch(hass, device=device, **s) for s in switches]
    async_add_entities(ents, update_before_add=True)

class MQTTSwitch(SwitchEntity):
    def __init__(self, hass, name, state_topic, command_topic, payload_on, payload_off, state_on, state_off, optimistic, qos, retain, icon=None, device=None):
        self._hass = hass
        self._name = name
        self._device = device
        #self._attr_unique_id = f"{state_topic}_switch"
        self._attr_unique_id = f"{device.lower()}_{state_topic.replace('/', '_')}_switch"
        self._attr_device_class = "switch"
        self._attr_icon = icon or "mdi:dip-switch"
        self._state_topic = state_topic
        self._command_topic = command_topic
        self._payload_on = payload_on
        self._payload_off = payload_off
        self._state_on = state_on
        self._state_off = state_off
        self._optimistic = optimistic
        self._qos = qos
        self._retain = retain
        self._is_on = False

    async def async_added_to_hass(self):
        await mqtt.async_subscribe(
            self._hass,
            self._state_topic,
            self._message_received,
            self._qos
        )

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._is_on

    @property
    def device_info(self):
        if not self._device:
            return None
        return {
            "identifiers": {(DOMAIN, self._device)},
            "name": f"{self._device} VBot Assistant",
            "manufacturer": "Vũ Tuyển",
            "model": "VBot Assistant MQTT"
        }

    async def async_turn_on(self, **kwargs):
        await mqtt.async_publish(self._hass, self._command_topic, self._payload_on, self._qos, self._retain)
        if self._optimistic:
            self._is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await mqtt.async_publish(self._hass, self._command_topic, self._payload_off, self._qos, self._retain)
        if self._optimistic:
            self._is_on = False
            self.async_write_ha_state()

    async def _message_received(self, msg):
        payload = msg.payload
        _LOGGER.debug(f"{self._name} MQTT nhận: {payload}")
        self._is_on = payload == self._state_on
        self.async_write_ha_state()
