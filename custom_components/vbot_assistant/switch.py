import logging
import voluptuous as vol
from datetime import timedelta, datetime
import aiohttp
import json
import base64
import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntity
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.event import async_call_later
from .const import DOMAIN, CONF_DEVICE_ID, VBot_URL_API

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    _LOGGER.error("VBot Assistant MQTT không hỗ trợ cấu hình YAML. Vui lòng dùng UI (config_entry).")
    pass

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("check_update_interface", True)
    hass.data[DOMAIN].setdefault("check_update_program", True)
    cfg = entry.data
    device = cfg.get(CONF_DEVICE_ID)
    vbot_url = cfg.get(VBot_URL_API)
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
    ]
    ents = [MQTTSwitch(hass, device=device, **s) for s in switches]
    hass.data[DOMAIN][VBot_URL_API] = vbot_url
    ents.append(VBotCheckAllUpdatesSwitch(hass, device))
    async_add_entities(ents, update_before_add=True)

class MQTTSwitch(SwitchEntity):
    def __init__(self, hass, name, state_topic, command_topic, payload_on, payload_off, state_on, state_off, optimistic, qos, retain, icon=None, device=None):
        self._hass = hass
        self._name = name
        self._device = device
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
        await mqtt.async_subscribe(self._hass, self._state_topic, self._message_received, self._qos)

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

#Lấy chỉ IP từ VBot URL config
def get_vbot_ip(hass):
    try:
        vbot_url = hass.data[DOMAIN].get(VBot_URL_API, "")
        if not vbot_url:
            _LOGGER.warning("❌ [VBot] Không có VBot URL trong config")
            return None
        clean_url = vbot_url.replace('http://', '').replace('https://', '').replace('www.', '')
        if ':' in clean_url:
            vbot_ip = clean_url.split(':')[0]
        else:
            vbot_ip = clean_url
        return vbot_ip.strip()
    except Exception as e:
        _LOGGER.error(f"❌ [VBot] Lỗi lấy VBot IP: {e}")
        return None

#Gửi notification
async def send_combined_vbot_notification(hass, updates, vbot_ip, device_id=None):
    try:
        if hass is None:
            return
        if not updates or not isinstance(updates, list):
            #_LOGGER.warning("[VBot] Updates không hợp lệ")
            return
        updates_count = len(updates)
        if updates_count == 0:
            #_LOGGER.warning("[VBot] Không có updates")
            return
        title = f"🚀 VBot {device_id or 'N/A'} - Có Bản Cập Nhật Mới!"
        notification_id = f"vbot_updates_{device_id.lower() if device_id else 'unknown'}"
        message_lines = [f"🔥 Có {updates_count} Nội Dung Cần Cập Nhật Cho {device_id or 'VBot'}:\n"]
        valid_updates = []
        for i, update in enumerate(updates):
            try:
                if not isinstance(update, dict) or not update:
                    continue
                required_keys = ['display_name', 'current_release_date', 'new_version_info']
                if not all(key in update for key in required_keys):
                    continue
                new_info = update['new_version_info']
                if not isinstance(new_info, dict) or not new_info.get('success'):
                    continue
                required_new_keys = ['version', 'release_date', 'description']
                if not all(key in new_info for key in required_new_keys):
                    continue
                valid_updates.append(update)
                display_name = update['display_name']
                current_date = update['current_release_date']
                version = new_info['version']
                new_date = new_info['release_date']
                description = new_info['description']
                block = f"""🔸 **{display_name}**
                        📦 Phiên Bản Mới: {version}
                        📅 Ngày Phát Hành: {new_date}
                        📝 Mô Tả: {description}
                        💻 Phiên Bản Hiện Tại: {current_date}
                        """
                message_lines.append(block)
            except Exception as e:
                #_LOGGER.debug(f"[VBot] Bỏ qua update {i}: {e}")
                continue
        if not valid_updates:
            _LOGGER.warning("⚠️ [VBot] Không có updates hợp lệ")
            return
        message_lines.extend(["",
            f"🕐 Thời Gian Kiểm Tra: {datetime.now().strftime('%H:%M, %d/%m/%Y')}",
            f"🔗 Kiểm tra: http://{vbot_ip}",
            f"🔗 https://github.com/marion001/VBot_Offline"
        ])
        message = "\n".join(message_lines)
        await hass.services.async_call("persistent_notification", "create", {"title": title, "message": message, "notification_id": notification_id})
    except Exception as e:
        _LOGGER.error(f"❌ [VBot] Lỗi send_combined_vbot_notification: {e}", exc_info=True)

#Kiểm tra phiên bản Online
async def fetch_github_version(session, repo_owner, repo_name, file_path, max_retries=3):
    for attempt in range(max_retries):
        try:
            github_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
            headers = {'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'VBot-Update-Checker/1.0'}
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            async with session.get(github_api_url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    api_data = await response.json()
                    content_b64 = api_data.get('content', '')
                    if not content_b64:
                        _LOGGER.warning(f"⚠️ [VBot] Không có content từ GitHub: {file_path}")
                        return {'success': False}
                    try:
                        content_bytes = base64.b64decode(content_b64)
                        content_json = json.loads(content_bytes.decode('utf-8'))
                        return {
                            'success': True,
                            'release_date': content_json.get('releaseDate'),
                            'version': content_json.get('version', ''),
                            'description': content_json.get('description', ''),
                            'github_sha': api_data.get('sha', '')
                        }
                    except (base64.binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as e:
                        _LOGGER.error(f"[VBot] Lỗi decode base64 từ API GitHub {file_path}: {e}")
                        return {'success': False}
                else:
                    error_text = await response.text()
                    _LOGGER.warning(f"⚠️ [VBot] GitHub API {response.status} (lần {attempt + 1}): {error_text}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return {'success': False}
        except asyncio.TimeoutError:
            _LOGGER.warning(f"⚠️ [VBot] Timeout GitHub API {file_path} (lần {attempt + 1}/{max_retries})")
        except Exception as e:
            _LOGGER.error(f"❌ [VBot] Lỗi GitHub API {file_path} (lần {attempt + 1}): {e}")
        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)
    _LOGGER.error(f"[VBot] ❌ Quá số lần thử lại khi kiểm tra phiên bản cho {file_path}")
    return {'success': False}

#Kiểm tra TẤT CẢ cập nhật và GỘP thành 1 notification
async def check_all_updates(hass, device_id=None):
    try:
        if not device_id:
            entries = hass.config_entries.async_entries(DOMAIN)
            if entries:
                device_id = entries[0].data.get(CONF_DEVICE_ID)
            if not device_id:
                _LOGGER.error("❌ [VBot] Không tìm thấy Device ID")
                return
        vbot_ip = get_vbot_ip(hass)
        if not vbot_ip:
            _LOGGER.error("❌ [VBot] Không lấy được IP")
            return
        tasks = [
            check_update_collect(hass, "interface", vbot_ip, "Có Phiên Bản Giao Diện Mới:", "html/Version.json"),
            check_update_collect(hass, "program", vbot_ip, "Có Phiên Bản Chương Trình Mới:", "Version.json")
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        updates = []
        for i, result in enumerate(results):
            #_LOGGER.debug(f"[VBot] Kết quả task {i}: type={type(result)}, value={result}")
            if (isinstance(result, dict) and 
                len(result) > 0 and 
                'new_version_info' in result and 
                result['new_version_info'] is not None and 
                isinstance(result['new_version_info'], dict) and
                result['new_version_info'].get('success') == True and
                'display_name' in result and 
                'current_release_date' in result):
                updates.append(result)
        if updates:
            await send_combined_vbot_notification(hass, updates, vbot_ip, device_id)
        else:
            notification_id = f"vbot_updates_{device_id.lower()}"
            try:
                await hass.services.async_call("persistent_notification", "dismiss", {"notification_id": notification_id})
            except Exception as e:
                _LOGGER.debug(f"[VBot] Không thể xóa notification: {e}")
            #_LOGGER.info("✅ [VBot] Không có cập nhật mới")
    except Exception as e:
        _LOGGER.error(f"❌ [VBot] Lỗi check_all_updates: {e}", exc_info=True)

#Kiểm tra 1 loại cập nhật và trả về kết quả
async def check_update_collect(hass, update_type, vbot_ip, display_name, github_path):
    result = {}
    try:
        file_path = "html/" if update_type == 'interface' else ""
        current_version_url = f"http://{vbot_ip}/includes/php_ajax/Show_file_path.php?read_file_path&file=/home/pi/VBot_Offline/{file_path}Version.json"
        #_LOGGER.debug(f"[VBot] Kiểm tra {display_name}: {current_version_url}")
        current_release_date = None
        new_version_info = None
        async with aiohttp.ClientSession() as session:
            #Lấy phiên bản hiện tại
            try:
                async with session.get(current_version_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        if response_data.get('success') == True:
                            data_str = response_data.get('data', '{}')
                            current_data = json.loads(data_str)
                            current_release_date = current_data.get('releaseDate')
                    else:
                        _LOGGER.warning(f"[VBot] HTTP {response.status} từ API {display_name}")
            except Exception as e:
                _LOGGER.warning(f"⚠️ [VBot] Lỗi API {display_name}: {e}")
            #Lấy GitHub version
            new_version_info = await fetch_github_version(session, "marion001", "VBot_Offline", github_path)
        if (current_release_date and 
            new_version_info and 
            isinstance(new_version_info, dict) and 
            new_version_info.get('success') == True and
            new_version_info.get('release_date')):
            new_release_date = new_version_info['release_date']
            if new_release_date != current_release_date:
                #_LOGGER.info(f"🔥 [VBot] CÓ CẬP NHẬT MỚI {display_name}! ({current_release_date} → {new_release_date})")
                result = {
                    'type': update_type,
                    'display_name': display_name,
                    'current_release_date': current_release_date,
                    'new_version_info': new_version_info
                }
        else:
            _LOGGER.warning(f"⚠️ [VBot] Không thể so sánh {display_name}")
    except Exception as e:
        _LOGGER.error(f"❌ [VBot] Lỗi check_update_collect {display_name}: {e}", exc_info=True)
    return result

#Lên lịch kiểm tra cập nhật phiên bản VBot
def schedule_update_task(hass, type_):
    interval = timedelta(minutes=2)
    async def task(_now):
        try:
            await check_all_updates(hass)
        except Exception as e:
            _LOGGER.error(f"[VBot] Lỗi auto check: {e}")
    tasks = hass.data[DOMAIN].get("update_tasks", {})
    if "all_updates" in tasks:
        old_handle = tasks["all_updates"]
        if callable(old_handle):
            try:
                old_handle()
            except:
                pass
    handle = async_track_time_interval(hass, task, interval)
    hass.data[DOMAIN].setdefault("update_tasks", {})
    hass.data[DOMAIN]["update_tasks"]["all_updates"] = handle

#Switch kiểm tra TẤT CẢ cập nhật VBot
class VBotCheckAllUpdatesSwitch(SwitchEntity, RestoreEntity):
    def __init__(self, hass, device):
        self.hass = hass
        self._device = device
        self._attr_name = f"Tự động kiểm tra cập nhật VBot ({device})"
        self._attr_unique_id = f"{device}_check_all_updates"
        self._attr_icon = "mdi:progress-upload"
        self._is_on = True
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN].setdefault("update_tasks", {})

    async def async_added_to_hass(self):
        last_state = await self.async_get_last_state()
        if last_state:
            self._is_on = last_state.state == "on"
        if self._is_on and "all_updates" not in self.hass.data[DOMAIN]["update_tasks"]:
            schedule_update_task(self.hass, "all")

    @property
    def is_on(self):
        return self._is_on

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device)},
            "name": f"VBot Assistant Updates {self._device}",
            "manufacturer": "Vũ Tuyển",
            "model": "VBot Assistant Custom Component"
        }

    @property
    def extra_state_attributes(self):
        """Hiển thị trạng thái cập nhật"""
        tasks = self.hass.data[DOMAIN].get("update_tasks", {})
        return {
            "last_check": "N/A",
            "auto_check_enabled": "all_updates" in tasks,
            "next_check": "30 minutes"
        }

    async def async_turn_on(self, **kwargs):
        self._is_on = True
        self.async_write_ha_state()
        if "all_updates" not in self.hass.data[DOMAIN]["update_tasks"]:
            schedule_update_task(self.hass, "all")
        await check_all_updates(self.hass, self._device)

    async def async_check_updates_service(self, call):
        await check_all_updates(self.hass, self._device)

    async def async_turn_off(self, **kwargs):
        self._is_on = False
        self.async_write_ha_state()
        tasks = self.hass.data[DOMAIN]["update_tasks"]
        if "all_updates" in tasks:
            handle = tasks.pop("all_updates")
            if callable(handle):
                handle()