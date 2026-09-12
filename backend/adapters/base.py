from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseIoTAdapter(ABC):
    """
    Standardized IoT Adapter Interface across all supported vendor ecosystems.
    """
    brand_name: str = "generic"

    @abstractmethod
    async def turn_on(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """Send power-on command to device."""
        pass

    @abstractmethod
    async def turn_off(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """Send power-off command to device."""
        pass

    @abstractmethod
    async def get_status(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """Query real-time device status."""
        pass

    @abstractmethod
    async def set_level(self, device: Dict[str, Any], parameter: str, value: int) -> Dict[str, Any]:
        """Adjust level parameter (e.g. brightness, volume, temperature)."""
        pass
