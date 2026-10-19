"""Serve the bundled card; users add the resource once in their dashboard."""
from pathlib import Path
from homeassistant.components.http import StaticPathConfig


async def async_setup_frontend(hass):
    await hass.http.async_register_static_paths([
        StaticPathConfig('/vbot_assistant/vbot-ultimate-card.js',
                         str(Path(__file__).parent/'www/vbot-ultimate-card.js'),False)
    ])
