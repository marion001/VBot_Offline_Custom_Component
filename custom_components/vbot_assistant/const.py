'''
Code By: Vũ Tuyển
GitHub VBot: https://github.com/marion001/VBot_Offline.git
Facebook Group: https://www.facebook.com/groups/1148385343358824
Facebook: https://www.facebook.com/TWFyaW9uMDAx
Mail: VBot.Assistant@gmail.com
'''

from urllib.parse import urlsplit, urlunsplit

DOMAIN = "vbot_assistant"
TTS_DOMAIN = DOMAIN

#Tên Client MQTT (Client ID MQTT) Của Loa VBot
CONF_DEVICE_ID = "device_id"

#URL API VBot: (IP:PORT <=> 192.168.14.194:5002)
VBot_URL_API = "vbot_url_api"
CONF_API_KEY = "vbot_api_key"
CONF_DEVICE_TYPE = "device_type"
CONF_AUTO_UPDATE_URL = "auto_update_url"
CONF_URL_SOURCE = "url_source"
CONF_MDNS_LAST_UPDATE = "mdns_last_update"
URL_SOURCE_MANUAL = "manual"
URL_SOURCE_MDNS = "mdns"
DEVICE_TYPE_HOST = "vbot_host"
DEVICE_TYPE_ANDROID = "android_client"
DEVICE_TYPE_ESP32 = "esp32_client"

HOST_PLATFORMS = ["switch", "number", "sensor", "select", "button", "text", "media_player"]
ANDROID_PLATFORMS = ["switch", "number", "sensor", "button", "text", "media_player"]
ESP32_PLATFORMS = ["switch", "number", "sensor", "button", "text", "media_player"]


def platforms_for_device(data: dict) -> list[str]:
    """Return only platforms implemented by the configured device profile."""
    if data.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_ANDROID:
        return ANDROID_PLATFORMS
    if data.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_ESP32:
        return ESP32_PLATFORMS
    return HOST_PLATFORMS


def normalize_vbot_url(value: str | None, device_type: str | None = None) -> str:
    """Return the API base URL, applying only the device profile's default port."""
    value = (value or "").strip().rstrip("/")
    if not value:
        return ""
    if value.startswith("//"):
        value = f"http:{value}"
    elif not value.lower().startswith(("http://", "https://")):
        value = f"http://{value}"
    parsed = urlsplit(value)
    default_port = {
        DEVICE_TYPE_HOST: 5002,
        DEVICE_TYPE_ANDROID: 8081,
    }.get(device_type)
    try:
        current_port = parsed.port
    except ValueError:
        return value
    if default_port and parsed.hostname and current_port is None:
        host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
        value = urlunsplit((parsed.scheme, f"{host}:{default_port}", parsed.path, parsed.query, parsed.fragment))
    return value


def vbot_api_headers(api_key: str | None) -> dict[str, str]:
    """Build the authentication header accepted by the VBot host API."""
    value = (api_key or "").strip()
    return {"VBot-API-Key": value} if value else {}
