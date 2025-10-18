from __future__ import annotations
from typing import Tuple, Mapping, Any
from abc import ABC, abstractmethod

class VoiceVendor(ABC):
    @abstractmethod
    async def start(self, payload: Mapping[str, Any]) -> Tuple[str, str]:
        """
        Return (connect_url, provider_call_id)
        connect_url is what the frontend opens.
        """
        ...
