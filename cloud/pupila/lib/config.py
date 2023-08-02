import os

from .singleton import Singleton
from .logger import logger

ENV_PREFIX = 'PUPILA'

def get_from_path(config, path):
    keys = path.split('.')
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            logger.warning(f'Missing {key} on the provided configuration. When reading {path}.')
            return None

    return value

def prioritized_config(config, path, env_var_name, type=str, required=False):
    value = get_from_path(config, path)

    value = type(os.environ.get(env_var_name, value))

    if required and value == None:
        logger.error(f'{env_var_name} or {path} config option is required!')
        sys.exit(1)

    return value

class Address():
    def __init__(self, address_dict, env_prefix):
        self._host = prioritized_config(address_dict, 'host', f'{env_prefix}_HOST', required=True)
        self._port = prioritized_config(address_dict, 'port', f'{env_prefix}_PORT', required=True)
    def get_host(self):
        return self._host
    def get_port(self):
        return self._port
    def get_address(self):
        return f'{self._host};{self._port}'

class Video():
    def __init__(self, video_dict, env_prefix):
        self._enable = prioritized_config(video_dict, 'enable', f'{env_prefix}_ENABLE', type=bool)
        self._uri = prioritized_config(video_dict, 'uri', f'{env_prefix}_URI', required=self._enable)

    def is_enabled(self):
        return self._enable
    def get_uri(self):
        return self._uri

class Input():
    def __init__(self, input_dict):
        self._video = Video(input_dict['video'], f'{ENV_PREFIX}_INPUT_VIDEO')
        self._address = Address(input_dict['address'], f'{ENV_PREFIX}_INPUT_ADDRESS')

    def get_video(self):
        return self._video
    def get_address(self):
        return self._address

class Config(metaclass=Singleton):
    def __init__(self, config_file_path):
        # TODO: parse config file path and delete mockup config
        config = {
            'input': {
                'video': {
                    'uri': 'some_hardcoded-uri'
                },
                'address': { # address where the input component runs for the nng connections
                    'host': 'localhost',
                    'port': 1234
                },
            },
            "test_mode": False,
        }

        # We follow a fail by default aproach. If a variable is required, it must be provided. There are no default values.
        # A user can use a default config file and override via env vars the configuration that it needs

        self._input = Input(config['input'])
        self._test_mode = prioritized_config(config, 'test_mode', f'{ENV_PREFIX}_TEST_MODE', type=bool)

    def get_input(self):
        return self._input
    def is_test_mode(self):
        return self._test_mode
