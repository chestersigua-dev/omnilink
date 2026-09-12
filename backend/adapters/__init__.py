from typing import Dict
from backend.adapters.base import BaseIoTAdapter
from backend.adapters.xiaomi import XiaomiMiioAdapter
from backend.adapters.tapo import TapoKlapAdapter
from backend.adapters.samsung import SamsungSmartAdapter
from backend.adapters.lg import LGWebOSAdapter
from backend.adapters.tcl import TCLAndroidTVAdapter

ADAPTER_REGISTRY: Dict[str, BaseIoTAdapter] = {
    "xiaomi": XiaomiMiioAdapter(),
    "tapo": TapoKlapAdapter(),
    "samsung": SamsungSmartAdapter(),
    "lg": LGWebOSAdapter(),
    "tcl": TCLAndroidTVAdapter(),
}

def get_adapter(brand: str) -> BaseIoTAdapter:
    """Retrieve the concrete adapter for a given brand, defaulting to Xiaomi if unknown."""
    brand_clean = (brand or "").lower().strip()
    return ADAPTER_REGISTRY.get(brand_clean, ADAPTER_REGISTRY["xiaomi"])
