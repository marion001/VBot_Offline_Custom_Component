'''
Code By: Vũ Tuyển
GitHub VBot: https://github.com/marion001/VBot_Offline.git
Facebook Group: https://www.facebook.com/groups/1148385343358824
Facebook: https://www.facebook.com/TWFyaW9uMDAx
Mail: VBot.Assistant@gmail.com
'''

DOMAIN = "vbot_assistant"
TTS_DOMAIN = DOMAIN

#Tên Client MQTT (Client ID MQTT) Của Loa VBot
CONF_DEVICE_ID = "device_id"

#URL API VBot: (IP:PORT <=> 192.168.14.194:5002)
VBot_URL_API = "vbot_url_api"
CONF_DEVICE_TYPE = "device_type"
DEVICE_TYPE_HOST = "vbot_host"
DEVICE_TYPE_ANDROID = "android_client"

HOST_PLATFORMS = ["switch", "number", "sensor", "select", "button", "text", "media_player"]
ANDROID_PLATFORMS = ["switch", "number", "sensor", "button", "text", "media_player"]


def platforms_for_device(data: dict) -> list[str]:
    """Return only platforms implemented by the configured device profile."""
    if data.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_ANDROID:
        return ANDROID_PLATFORMS
    return HOST_PLATFORMS


def normalize_vbot_url(value: str | None) -> str:
    """Return a usable HTTP base URL while preserving local/LAN addresses."""
    value = (value or "").strip().rstrip("/")
    if not value:
        return ""
    if not value.startswith(("http://", "https://")):
        value = f"http://{value}"
    return value
