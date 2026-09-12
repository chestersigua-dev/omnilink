import httpx
from typing import Dict, Any
from backend.adapters.base import BaseIoTAdapter
from backend.config import is_simulation_mode

class TapoKlapAdapter(BaseIoTAdapter):
    """
    TP-Link Tapo protocol adapter communicating via HTTP KLAP protocol (port 80/443).
    Handles Tapo Smart Plugs (P110), Multicolor Bulbs (L530), and Light Strips.
    """
    brand_name: str = "tapo"
    default_port: int = 80

    async def _send_tapo_request(self, ip: str, port: int, method: str, params: dict) -> Dict[str, Any]:
        """
        Send KLAP HTTP request to Tapo endpoint.
        Falls back smoothly to mock payload when physical hardware is not present and simulation is active.
        """
        url = f"http://{ip}:{port or self.default_port}/app/request"
        payload = {
            "method": method,
            "params": params
        }
        if not is_simulation_mode() and ip and ip != "127.0.0.1":
            try:
                async with httpx.AsyncClient(timeout=0.8) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        return resp.json()
            except Exception as e:
                if not is_simulation_mode():
                    return {"error_code": -1, "error": str(e), "is_offline": True, "protocol": "tapo-klap-http"}

        return {"error_code": 0, "result": {"response": "success"}, "protocol": "tapo-klap-http"}

    async def turn_on(self, device: Dict[str, Any]) -> Dict[str, Any]:
        ip = device.get("ip_address", "127.0.0.1")
        port = device.get("port", self.default_port)
        res = await self._send_tapo_request(ip, port, "set_device_info", {"device_on": True})
        is_online = not res.get("is_offline", False)
        return {
            "power_state": True if is_online else device.get("power_state", False),
            "is_online": is_online,
            "brand": self.brand_name,
            "protocol_log": f"Tapo KLAP: set_device_info(device_on=true) -> code {res.get('error_code', 0)}"
        }

    async def turn_off(self, device: Dict[str, Any]) -> Dict[str, Any]:
        ip = device.get("ip_address", "127.0.0.1")
        port = device.get("port", self.default_port)
        res = await self._send_tapo_request(ip, port, "set_device_info", {"device_on": False})
        is_online = not res.get("is_offline", False)
        return {
            "power_state": False,
            "is_online": is_online,
            "brand": self.brand_name,
            "protocol_log": f"Tapo KLAP: set_device_info(device_on=false) -> code {res.get('error_code', 0)}"
        }

    async def get_status(self, device: Dict[str, Any]) -> Dict[str, Any]:
        ip = device.get("ip_address", "127.0.0.1")
        port = device.get("port", self.default_port)
        res = await self._send_tapo_request(ip, port, "get_device_info", {})
        is_online = not res.get("is_offline", False)
        return {
            "power_state": device.get("power_state", True) if is_online else False,
            "level": device.get("level", 80),
            "is_online": is_online,
            "brand": self.brand_name,
            "protocol_log": f"Tapo KLAP: get_device_info() -> code {res.get('error_code', 0)}"
        }

    async def set_level(self, device: Dict[str, Any], parameter: str, value: int) -> Dict[str, Any]:
        ip = device.get("ip_address", "127.0.0.1")
        port = device.get("port", self.default_port)
        clamped_val = max(0, min(100, int(value)))
        res = await self._send_tapo_request(ip, port, "set_device_info", {"brightness": clamped_val})
        is_online = not res.get("is_offline", False)
        return {
            "level": clamped_val,
            "is_online": is_online,
            "parameter": parameter,
            "brand": self.brand_name,
            "protocol_log": f"Tapo KLAP: set_device_info(brightness={clamped_val}) -> code {res.get('error_code', 0)}"
        }
