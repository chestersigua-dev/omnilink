import asyncio
import socket
import logging
from typing import List, Dict, Any
from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
from backend.config import SIMULATION_MODE

logger = logging.getLogger("omnilink.scanner")

# Standard 5-brand virtual devices for Capstone Demonstration / Defense Mode
SIMULATED_DEVICES: List[Dict[str, Any]] = [
    {
        "device_uid": "SIM_XIAOMI_PURIFIER_01",
        "name": "Xiaomi Smart Air Purifier 4 Pro",
        "brand": "xiaomi",
        "model": "zhimi.airpurifier.v7",
        "device_type": "purifier",
        "ip_address": "192.168.1.101",
        "mac_address": "50:EC:50:A1:02:11",
        "port": 54321,
        "protocol": "miio-udp-jsonrpc",
        "is_online": True,
        "power_state": True,
        "level": 75,
        "state_metadata": {"filter_life": 92, "aqi": 14, "mode": "auto"}
    },
    {
        "device_uid": "SIM_TAPO_BULB_02",
        "name": "TP-Link Tapo L530 Smart Bulb",
        "brand": "tapo",
        "model": "Tapo-L530E-Multicolor",
        "device_type": "bulb",
        "ip_address": "192.168.1.102",
        "mac_address": "E8:48:B8:33:14:52",
        "port": 80,
        "protocol": "klap-http",
        "is_online": True,
        "power_state": True,
        "level": 85,
        "state_metadata": {"hue": 210, "saturation": 90, "color_temp": 4000}
    },
    {
        "device_uid": "SIM_SAMSUNG_TV_03",
        "name": "Samsung 65\" Neo QLED 8K TV",
        "brand": "samsung",
        "model": "QN65QN900B-Tizen",
        "device_type": "tv",
        "ip_address": "192.168.1.103",
        "mac_address": "48:44:F7:55:22:98",
        "port": 8001,
        "protocol": "tizen-ws-remote",
        "is_online": True,
        "power_state": False,
        "level": 22,
        "state_metadata": {"input": "HDMI 1", "resolution": "7680x4320"}
    },
    {
        "device_uid": "SIM_LG_TV_04",
        "name": "LG OLED C3 Cinema Display",
        "brand": "lg",
        "model": "OLED65C3PSA-webOS",
        "device_type": "tv",
        "ip_address": "192.168.1.104",
        "mac_address": "A8:23:FE:12:44:81",
        "port": 3000,
        "protocol": "webos-ssap-ws",
        "is_online": True,
        "power_state": True,
        "level": 35,
        "state_metadata": {"appId": "netflix", "sound_output": "arc"}
    },
    {
        "device_uid": "SIM_TCL_AC_05",
        "name": "TCL FreshIN Smart Air Conditioner",
        "brand": "tcl",
        "model": "TAC-12CHSD-Inverter",
        "device_type": "ac",
        "ip_address": "192.168.1.105",
        "mac_address": "00:E0:4C:89:12:67",
        "port": 5555,
        "protocol": "adb-tcp-keyevent",
        "is_online": True,
        "power_state": True,
        "level": 23, # Target temperature 23°C
        "state_metadata": {"mode": "cool", "fan_speed": "turbo"}
    }
]

class MDNSCollector(ServiceListener):
    def __init__(self):
        self.discovered: List[Dict[str, Any]] = []

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        try:
            info = zc.get_service_info(type_, name)
            if info:
                addresses = [socket.inet_ntoa(addr) for addr in info.addresses if len(addr) == 4]
                ip = addresses[0] if addresses else "127.0.0.1"
                self.discovered.append({
                    "name": name.split(".")[0],
                    "type": type_,
                    "ip": ip,
                    "port": info.port or 80,
                    "server": info.server
                })
        except Exception:
            pass

async def scan_ssdp(timeout: float = 1.0) -> List[Dict[str, Any]]:
    """Send SSDP M-SEARCH broadcast over UDP port 1900 to discover UPnP devices."""
    ssdp_target = ("239.255.255.250", 1900)
    query = (
        'M-SEARCH * HTTP/1.1\r\n'
        'HOST: 239.255.255.250:1900\r\n'
        'MAN: "ssdp:discover"\r\n'
        'MX: 1\r\n'
        'ST: ssdp:all\r\n'
        '\r\n'
    ).encode("utf-8")

    discovered = []
    loop = asyncio.get_running_loop()

    def _broadcast():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        try:
            sock.sendto(query, ssdp_target)
            while True:
                try:
                    data, addr = sock.recvfrom(2048)
                    headers = data.decode("utf-8", errors="ignore")
                    discovered.append({"ip": addr[0], "port": addr[1], "raw": headers})
                except socket.timeout:
                    break
        except Exception:
            pass
        finally:
            sock.close()

    try:
        await loop.run_in_executor(None, _broadcast)
    except Exception:
        pass
    return discovered

async def scan_network(force_simulation: bool = False) -> List[Dict[str, Any]]:
    """
    Perform local subnet IoT discovery using mDNS & SSDP broadcast.
    If simulation mode is active or no physical IoT units respond,
    returns the complete 5-brand virtual device catalog.
    """
    real_results = []

    if not force_simulation and not SIMULATION_MODE:
        try:
            # 1. mDNS Scan
            zc = Zeroconf()
            collector = MDNSCollector()
            service_types = [
                "_http._tcp.local.",
                "_miio._udp.local.",
                "_googlecast._tcp.local.",
                "_airplay._tcp.local."
            ]
            browser = ServiceBrowser(zc, service_types, collector)
            await asyncio.sleep(1.2)
            zc.close()

            # 2. SSDP UPnP Scan
            ssdp_devs = await scan_ssdp(timeout=0.8)

            for m in collector.discovered:
                real_results.append({
                    "device_uid": f"MDNS_{m['ip'].replace('.', '_')}_{m['port']}",
                    "name": m["name"],
                    "brand": "xiaomi" if "miio" in m.get("type", "") else "generic",
                    "model": m.get("server", "Network Device"),
                    "device_type": "network_device",
                    "ip_address": m["ip"],
                    "mac_address": "00:00:00:00:00:00",
                    "port": m["port"],
                    "protocol": "mdns-zeroconf",
                    "is_online": True,
                    "power_state": True,
                    "level": 50,
                    "state_metadata": {"discovery_source": "mDNS"}
                })

            for s in ssdp_devs:
                real_results.append({
                    "device_uid": f"SSDP_{s['ip'].replace('.', '_')}",
                    "name": f"UPnP Device ({s['ip']})",
                    "brand": "samsung" if "samsung" in s["raw"].lower() else "lg" if "lg" in s["raw"].lower() else "generic",
                    "model": "SSDP Root Device",
                    "device_type": "tv",
                    "ip_address": s["ip"],
                    "mac_address": "00:00:00:00:00:00",
                    "port": s["port"],
                    "protocol": "ssdp-upnp",
                    "is_online": True,
                    "power_state": True,
                    "level": 50,
                    "state_metadata": {"discovery_source": "SSDP"}
                })
        except Exception as e:
            logger.warning(f"Live network scan exception: {e}")

    # If simulation mode is requested or no physical IoT items were found in the current environment:
    if force_simulation or SIMULATION_MODE or len(real_results) == 0:
        return SIMULATED_DEVICES

    return real_results
