import re
from typing import Any, Dict
from colorama import Fore, Style

class BaseLogFormatter:
    def __init__(self):
        self._last_component = None
        self._startup_phase = None

    def _simplify_component_name(self, name: str) -> str:
        return name.split('.')[-1]

    def _extract_component(self, message: str) -> str:
        match = re.search(r'Initializing (\w+)', message)
        return match.group(1) if match else ""

    def format_extra(self, extra: Dict[str, Any]) -> str:
        if not extra:
            return ""

        relevant_info = {
            k: v for k, v in extra.items()
            if k not in ['component', 'operation'] or 'error' in k
        }

        if not relevant_info:
            return ""

        formatted_items = []
        for key, value in relevant_info.items():
            colored_value = f"{Fore.CYAN}{value}{Style.RESET_ALL}"
            formatted_items.append(f"{key}={colored_value}")

        return f" ({' | '.join(formatted_items)})"
