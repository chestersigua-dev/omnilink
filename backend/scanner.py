import asyncio
import socket
import logging
from typing import List, Dict, Any, Optional
from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
from backend.config import SIMULATION_MODE, is_simulation_mode

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
                # Filter out loopback
                if ip.startswith("127."):
                    return
                self.discovered.append({
                    "name": name.split(".")[0],
                    "type": type_,
                    "ip": ip,
                    "port": info.port or 80,
                    "server": info.server or "mDNS Node"
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

def _classify_ssdp_device(s: Dict[str, Any]) -> Dict[str, Any]:
    """Parse raw SSDP response headers and classify brand, model, and device type."""
    raw = s.get("raw", "").lower()
    ip = s.get("ip", "127.0.0.1")
    port = s.get("port", 1900)

    brand = "generic"
    device_type = "network_device"
    name = f"UPnP Device ({ip})"
    model = "SSDP Device"

    if "samsung" in raw or "sec" in raw or "tizen" in raw:
        brand = "samsung"
        device_type = "tv"
        name = f"Samsung Smart TV ({ip})"
        model = "Tizen Smart TV"
    elif "lg" in raw or "webos" in raw or "lge" in raw:
        brand = "lg"
        device_type = "tv"
        name = f"LG webOS Device ({ip})"
        model = "LG webOS Display"
    elif "roku" in raw or "tcl" in raw:
        brand = "tcl"
        device_type = "tv"
        name = f"TCL / Roku Device ({ip})"
        model = "Roku Smart TV"
    elif "tapo" in raw or "tp-link" in raw or "tplink" in raw:
        brand = "tapo"
        device_type = "plug"
        name = f"Tapo Smart Device ({ip})"
        model = "TP-Link Tapo"
    elif "xiaomi" in raw or "miio" in raw or "yeelight" in raw:
        brand = "xiaomi"
        device_type = "purifier"
        name = f"Xiaomi Smart Appliance ({ip})"
        model = "Mi Smart Hardware"
    elif "philips" in raw or "hue" in raw:
        brand = "generic"
        device_type = "bulb"
        name = f"Philips Hue Bridge ({ip})"
        model = "Hue Bridge"
    elif "sonos" in raw:
        brand = "generic"
        device_type = "speaker"
        name = f"Sonos Speaker ({ip})"
        model = "Sonos HiFi"
    elif "chromecast" in raw or "google" in raw:
        brand = "generic"
        device_type = "tv"
        name = f"Google Cast Device ({ip})"
        model = "Chromecast"

    # Extract LOCATION header if present
    location = None
    for line in s.get("raw", "").splitlines():
        if line.lower().startswith("location:"):
            location = line.split(":", 1)[1].strip()
            break

    return {
        "device_uid": f"SSDP_{ip.replace('.', '_')}",
        "name": name,
        "brand": brand,
        "model": model,
        "device_type": device_type,
        "ip_address": ip,
        "mac_address": "00:00:00:00:00:00",
        "port": port,
        "protocol": "ssdp-upnp",
        "is_online": True,
        "power_state": True,
        "level": 50,
        "state_metadata": {
            "discovery_source": "SSDP UPnP",
            "location": location or ""
        }
    }

async def scan_network(
    force_simulation: Optional[bool] = None,
    disable_simulation: bool = False
) -> List[Dict[str, Any]]:
    """
    Perform local subnet IoT discovery using mDNS & SSDP broadcast.

    - If disable_simulation is True: strictly scans the physical local network
      and returns only real devices detected. Never injects simulated devices.
    - If force_simulation is True: immediately returns the 5-brand virtual device catalog.
    - If neither is explicitly passed: follows the system's runtime simulation mode configuration.
    """
    # Determine whether simulation should run
    if disable_simulation:
        should_simulate = False
    elif force_simulation is not None:
        should_simulate = bool(force_simulation)
    else:
        should_simulate = is_simulation_mode()

    if should_simulate:
        logger.info("Returning simulated 5-brand device catalog (simulation mode active).")
        return list(SIMULATED_DEVICES)

    logger.info("Running live physical network scan (simulation DISABLED)...")
    real_devices_by_ip: Dict[str, Dict[str, Any]] = {}

    try:
        # 1. mDNS Scan
        zc = Zeroconf()
        collector = MDNSCollector()
        service_types = [
            "_http._tcp.local.",
            "_miio._udp.local.",
            "_googlecast._tcp.local.",
            "_airplay._tcp.local.",
            "_hap._tcp.local.",
            "_spotify-connect._tcp.local.",
            "_sonos._tcp.local.",
            "_roku-rcp._tcp.local.",
            "_hue._tcp.local.",
            "_smartthings._tcp.local."
        ]
        browser = ServiceBrowser(zc, service_types, collector)
        await asyncio.sleep(1.2)
        zc.close()

        # Deduplicate and register mDNS devices
        for m in collector.discovered:
            ip = m["ip"]
            brand = "xiaomi" if "miio" in m.get("type", "").lower() else "generic"
            dev_type = "purifier" if brand == "xiaomi" else "network_device"
            server_str = m.get("server", "Network Device")
            
            # Additional brand inference from name / server
            lower_name = (m["name"] + " " + server_str).lower()
            if "tapo" in lower_name or "tp-link" in lower_name:
                brand = "tapo"
                dev_type = "plug"
            elif "samsung" in lower_name:
                brand = "samsung"
                dev_type = "tv"
            elif "lg" in lower_name or "webos" in lower_name:
                brand = "lg"
                dev_type = "tv"
            elif "tcl" in lower_name or "roku" in lower_name:
                brand = "tcl"
                dev_type = "tv"

            real_devices_by_ip[ip] = {
                "device_uid": f"MDNS_{ip.replace('.', '_')}_{m['port']}",
                "name": m["name"],
                "brand": brand,
                "model": server_str,
                "device_type": dev_type,
                "ip_address": ip,
                "mac_address": "00:00:00:00:00:00",
                "port": m["port"],
                "protocol": "mdns-zeroconf",
                "is_online": True,
                "power_state": True,
                "level": 50,
                "state_metadata": {"discovery_source": "mDNS", "service_type": m.get("type", "")}
            }

        # 2. SSDP UPnP Scan
        ssdp_devs = await scan_ssdp(timeout=0.8)
        for s in ssdp_devs:
            ip = s["ip"]
            classified = _classify_ssdp_device(s)
            # If we already have mDNS info, enrich it; otherwise add SSDP entry
            if ip in real_devices_by_ip:
                if classified["brand"] != "generic" and real_devices_by_ip[ip]["brand"] == "generic":
                    real_devices_by_ip[ip]["brand"] = classified["brand"]
                    real_devices_by_ip[ip]["device_type"] = classified["device_type"]
                    real_devices_by_ip[ip]["name"] = classified["name"]
                real_devices_by_ip[ip]["state_metadata"]["ssdp_location"] = classified["state_metadata"]["location"]
            else:
                real_devices_by_ip[ip] = classified

    except Exception as e:
        logger.warning(f"Live physical network scan exception: {e}")

    # Return only physically discovered units (empty list if none found on LAN)
    return list(real_devices_by_ip.values())
