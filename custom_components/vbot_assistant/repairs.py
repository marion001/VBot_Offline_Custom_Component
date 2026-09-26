"""Actionable Home Assistant repair issues for VBot Assistant."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN


def _issue_id(kind: str, device_id: str) -> str:
    return f"{kind}_{device_id.casefold()}"


@callback
def create_duplicate_device_issue(
    hass: HomeAssistant,
    device_id: str,
    conflicting_title: str,
) -> None:
    """Report a case-insensitive MQTT Client ID collision."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id("duplicate_device_id", device_id),
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="duplicate_device_id",
        translation_placeholders={
            "device_id": device_id,
            "conflicting_title": conflicting_title,
        },
    )


@callback
def delete_duplicate_device_issue(hass: HomeAssistant, device_id: str) -> None:
    """Clear a resolved MQTT Client ID collision."""
    ir.async_delete_issue(
        hass, DOMAIN, _issue_id("duplicate_device_id", device_id)
    )


@callback
def update_media_api_issue(
    hass: HomeAssistant,
    device_id: str,
    *,
    compatible: bool,
    current_version: int | None,
    minimum_version: int,
    missing_capabilities: list[str],
) -> None:
    """Create or clear the repair for an outdated WebUI Media API."""
    issue_id = _issue_id("media_api_outdated", device_id)
    if compatible:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="media_api_outdated",
        translation_placeholders={
            "device_id": device_id,
            "current_version": str(current_version or "unknown"),
            "minimum_version": str(minimum_version),
            "missing_capabilities": ", ".join(missing_capabilities) or "none",
        },
    )


@callback
def update_api_auth_issue(
    hass: HomeAssistant, device_id: str, *, authentication_failed: bool
) -> None:
    """Create or clear the API authentication repair issue."""
    issue_id = _issue_id("api_auth_failed", device_id)
    if not authentication_failed:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="api_auth_failed",
        translation_placeholders={"device_id": device_id},
    )
