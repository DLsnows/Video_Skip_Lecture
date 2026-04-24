import json
import os
import sys
from typing import Dict, Any, Optional

class ConfigManager:
    def __init__(self, config_file: str = None):
        self.config_file = config_file or self._get_default_config_path()
        self.default_config = {
            "transcription_provider": {
                "base_url": "",
                "api_key": "",
                "model": "whisper-large-v3"
            },
            "ocr_provider": {
                "base_url": "",
                "api_key": "",
                "model": "deepseek-ai/DeepSeek-OCR"
            },
            "summarization_provider": {
                "base_url": "https://api.deepseek.com",
                "api_key": "",
                "model": "deepseek-reasoner"
            },
            "folders": {
                "default_input": "",
                "default_output": ""
            }
        }

    @staticmethod
    def _get_default_config_path() -> str:
        """Get the config file path suitable for the current runtime mode.

        - PyInstaller (sys._MEIPASS exists): save alongside the exe for persistence
        - Dev mode: save in the current working directory
        """
        if getattr(sys, '_MEIPASS', False):
            return os.path.join(os.path.dirname(sys.executable), "config.json")
        return os.path.abspath("config.json")

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return self._merge_configs(self.default_config, config)
            except (json.JSONDecodeError, FileNotFoundError):
                # If there's an error loading, return defaults
                return self.default_config
        else:
            return self.default_config

    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file"""
        try:
            # Merge with defaults to ensure all keys exist
            merged_config = self._merge_configs(self.default_config, config)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(merged_config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get_setting(self, key: str, subkey: str = None) -> Any:
        """Get a specific setting value"""
        config = self.load_config()

        if subkey:
            return config.get(key, {}).get(subkey)
        else:
            return config.get(key)

    def update_setting(self, key: str, value: Any, subkey: str = None) -> bool:
        """Update a specific setting"""
        config = self.load_config()

        if subkey:
            if key not in config:
                config[key] = {}
            config[key][subkey] = value
        else:
            config[key] = value

        return self.save_config(config)

    def _merge_configs(self, default: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge default config with overrides"""
        result = default.copy()

        for key, value in override.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    # Compatibility methods for the API routes
    @property
    def config(self) -> Dict[str, Any]:
        """Return the current config (for compatibility with original API)"""
        return self.load_config()

    def set_setting(self, key: str, value: Any) -> None:
        """Set a setting by key path (for compatibility with original API)"""
        keys = key.split('.')
        config = self.load_config()

        config_ref = config
        for k in keys[:-1]:
            if k not in config_ref:
                config_ref[k] = {}
            config_ref = config_ref[k]

        config_ref[keys[-1]] = value
        self.save_config(config)

    def get_setting_by_path(self, key: str, default: Any = None) -> Any:
        """Get a setting by dot notation path (for compatibility with original API)"""
        keys = key.split('.')
        value = self.load_config()

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

# Global instance
config_manager = ConfigManager()