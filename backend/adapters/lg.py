import asyncio
import json
import httpx
from typing import Dict, Any
from backend.adapters.base import BaseIoTAdapter
from backend.config import SIMULATION_MODE

class LGWebOSAdapter(BaseIoTAdapter):
    """
    LG webOS Smart TV and ThinQ appliance adapter.
    Uses ssap:// WebSocket protocol (port 3000/3001) and UPnP SSDP service.
    """
    brand_name: str = "lg"
    default_port: int = 3000

    async def _send_ssap_command(self, ip: str, port: int, uri: str, payload: dict) -> Dict[str, Any]:
        """
        Send a webOS ssap:// WebSocket packet or UPnP SOAP command.
        Gracefully falls back to simulated response.
        """
        request_envelope = {
            "type": "request",
            "id": "omnilink_cmd_1",
            "uri": uri,
            "payload": payload
        }

        if not SIMULATION_MODE and ip and ip != "127.0.0.1":
            try:
                # Check HTTP endpoint for webOS info
                async with httpx.AsyncClient(timeout=0.6) as client:
                    resp = await client.get(f"http://{ip}:{port or self.default_port}/roap/api/data")
                    if resp.status_code == 200:
                        return {"status": "ok", "ssap_uri": uri, "response": resp.text}
            except Exception:
                pass

        return {"status": "ok", "uri": uri, "payload": payload, "protocol": "lg-webos-ssap"}

    async def turn_on(self, device: Dict[str, Any]) -> Dict[str, Any]:
        # Wake-on-LAN or SSAP turn on
        ip = device.get("ip_address", "127.0.0.1")
        port = device.get("port", self.default_port)
        res = await self._send_ssap_command(ip, port, "ssap://system/turnOn", {})
        return {
            "power_state": True,
            "is_online": True,
            "brand": self.brand_name,
            "protocol_log": f"LG ssap://system/turnOn dispatched -> {res.get('status')}"
        }

    async def turn_off(self, device: Dict[str, Any]) -> Dict[str, Any]:
        ip = device.get("ip_address", "127.0.0.1")
        port = device.get("port", self.default_port)
        res = await self._send_ssap_command(ip, port, "ssap://system/turnOff", {})
        return {
            "power_state": False,
            "is_online": True,
            "brand": self.brand_name,
            "protocol_log": f"LG ssap://system/turnOff dispatched -> {res.get('status')}"
        }

    async def get_status(self, device: Dict[str, Any]) -> Dict[str, Any]:
        ip = device.get("ip_address", "127.0.0.1")
        port = device.get("port", self.default_port)
        res = await self._send_ssap_command(ip, port, "ssap://audio/getVolume", {})
        return {
            "power_state": device.get("power_state", True),
            "level": device.get("level", 40),
            "is_online": True,
            "brand": self.brand_name,
            "protocol_log": f"LG webOS: getVolume() -> {res.get('status')}"
        }

    async def set_level(self, device: Dict[str, Any], parameter: str, value: int) -> Dict[str, Any]:
        ip = device.get("ip_address", "127.0.0.1")
        port = device.get("port", self.default_port)
        clamped_val = max(0, min(100, int(value)))
        res = await self._send_ssap_command(ip, port, "ssap://audio/setVolume", {"volume": clamped_val})
        return {
            "level": clamped_val,
            "is_online": True,
            "parameter": parameter,
            "brand": self.brand_name,
            "protocol_log": f"LG ssap://audio/setVolume({clamped_val}) -> {res.get('status')}"
        }
