"""Configuration Mutator Service with atomic persistence and validation (<90 LOC)."""

import logging
import os
from pathlib import Path
from typing import Any, List, Optional
import yaml

from abi_coach.infrastructure.config.settings import AppConfig

logger = logging.getLogger(__name__)


class ConfigMutator:
    """Atomic configuration mutator for AppConfig and config.yaml (<90 LOC)."""

    def __init__(self, config_path: str = "config.yaml", config: Optional[AppConfig] = None):
        self.config_path = config_path
        self.config = config

    def mutate(self, key_path: List[str], value: Any) -> bool:
        """Mutate in-memory config attribute and persist to config.yaml atomically."""
        if not key_path or not all(isinstance(k, str) and k for k in key_path):
            return False
        if self.config is not None:
            self._update_in_memory(key_path, value)
        return self.save_key(key_path, value)

    def _update_in_memory(self, key_path: List[str], value: Any) -> bool:
        """Traverse nested attributes of AppConfig and set the target value."""
        try:
            target: Any = self.config
            for k in key_path[:-1]:
                target = getattr(target, k)
            setattr(target, key_path[-1], value)
            return True
        except Exception as exc:
            logger.warning("Failed in-memory update for %s: %s", key_path, exc)
            return False

    def save_key(self, key_path: List[str], value: Any) -> bool:
        """Atomically patch a nested key in config.yaml preserving existing contents."""
        if not key_path:
            return False
        path = Path(self.config_path)
        if not path.is_file():
            logger.debug("Config file %s does not exist, skipping persistence.", path)
            return False

        tmp_path = path.with_suffix(f".tmp_{os.getpid()}")
        try:
            content = path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                data = {}

            cur = data
            for k in key_path[:-1]:
                if k not in cur or not isinstance(cur[k], dict):
                    cur[k] = {}
                cur = cur[k]
            cur[key_path[-1]] = value

            dumped = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
            tmp_path.write_text(dumped, encoding="utf-8")
            tmp_path.replace(path)
            return True
        except Exception as exc:
            logger.error("Failed to atomic-write config key %s to %s: %s", key_path, path, exc)
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            return False
