import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

class Config:
    """Configuration management for OpenClip."""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if Config._config is not None:
            return
        
        # Default configuration (matching config.yaml structure)
        self._config = {
            'system': {
                'gpu_enabled': 'auto',
                'log_level': 'INFO',
                'output_dir': 'output',
                'download_dir': 'downloads'
            },
            'models': {
                'transcriber': {
                    'size': 'small',
                    'device': 'auto',
                    'compute_type': 'int8'
                },
                'analyzer': {
                    'model_name': 'gemini-2.0-flash',
                    'max_retries': 5,
                    'base_delay': 10
                }
            },
            'video': {
                'target_resolution': [1080, 1920],
                'crop_strategy': 'center',
                'subtitle': {
                    'enabled': True,
                    'font': 'Arial-Bold',
                    'font_size': 70,
                    'color': 'yellow',
                    'stroke_color': 'black',
                    'stroke_width': 2
                }
            },
            'upload': {
                'browser_profile': None,
                'headless': False
            },
            # Legacy compatibility mappings
            'transcription': {
                'model_size': 'small',
                'device': 'auto',
                'compute_type': 'auto'
            },
            'analysis': {
                'model': 'gemini-2.0-flash',
                'min_clip_length': 30,
                'max_clip_length': 60,
                'min_virality_score': 7,
                'max_clips': 3,
                'content_type': 'auto'
            },
            'editing': {
                'output_dir': 'output',
                'subtitle': {
                    'enabled': True,
                    'style': 'sentence',
                    'font': 'Arial-Bold',
                    'fontsize': 70,
                    'color': 'yellow',
                    'stroke_color': 'black',
                    'stroke_width': 2,
                    'position': 'bottom',
                    'relative_position': 0.8
                },
                'video': {
                    'resolution': '1080x1920',
                    'zoom_enabled': False,
                    'pan_enabled': False,
                    'audio_normalize': True
                }
            },
            'downloader': {
                'download_dir': 'downloads',
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            },
            'cache': {
                'enabled': True,
                'cache_dir': '.cache',
                'ttl_days': 30
            },
            'logging': {
                'level': 'INFO',
                'verbose': False,
                'quiet': False
            },
            'processing': {
                'workers': 1,
                'parallel_clips': False
            }
        }
        
        # Load from config file if exists
        config_path = Path('config.yaml')
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    file_config = yaml.safe_load(f) or {}
                    self._merge_config(self._config, file_config)
                    # Sync new structure to legacy keys for backward compatibility
                    self._sync_legacy_config()
            except Exception as e:
                print(f"Warning: Could not load config.yaml: {e}")
    
    def _sync_legacy_config(self):
        """Sync new config structure to legacy keys for backward compatibility."""
        # Sync transcription settings
        if 'models' in self._config and 'transcriber' in self._config['models']:
            trans = self._config['models']['transcriber']
            self._config['transcription'] = {
                'model_size': self._config['models']['transcriber'].get('size', 'small'),
                'device': self._config['models']['transcriber'].get('device', 'auto'),
                'compute_type': self._config['models']['transcriber'].get('compute_type', 'int8')
            }
        
        # Sync system settings
        if 'system' in self._config:
            sys_conf = self._config['system']
            self._config['downloader'] = {
                'download_dir': self._config['system'].get('download_dir', 'downloads'),
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            }
            self._config['logging'] = {
                'level': sys_conf.get('log_level', 'INFO'),
                'verbose': False,
                'quiet': False
            }
        
        # Sync video settings
        if 'video' in self._config:
            vid_conf = self._config['video']
            self._config['editing'] = {
                'output_dir': self._config['system'].get('output_dir', 'output'),
                'subtitle': vid_conf.get('subtitle', {}),
                'video': {
                    'resolution': f"{vid_conf.get('target_resolution', [1080, 1920])[0]}x{vid_conf.get('target_resolution', [1080, 1920])[1]}",
                    'zoom_enabled': False,
                    'pan_enabled': False,
                    'audio_normalize': True
                }
            }
    
    def _merge_config(self, base: Dict, override: Dict):
        """Recursively merge override config into base config."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get config value by dot-separated path (e.g., 'transcription.model_size')."""
        keys = key_path.split('.')
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, key_path: str, value: Any):
        """Set config value by dot-separated path."""
        keys = key_path.split('.')
        config = self._config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
    
    def save(self, path: Optional[str] = None):
        """Save current configuration to YAML file."""
        if path is None:
            path = 'config.yaml'
        
        with open(path, 'w') as f:
            yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
    
    def get_all(self) -> Dict:
        """Get entire configuration dictionary."""
        return self._config.copy()

# Global config instance
_config = None

def get_config():
    """Get the global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


