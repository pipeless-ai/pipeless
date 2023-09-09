import os
import re
import sys

from pipeless_ai.lib.singleton import Singleton
from pipeless_ai.lib.logger import logger

ENV_PREFIX = 'PIPELESS'

def prioritized_config(config, path, env_var_name, convert_to=str, required=False, default=None):
    value = dict.get(config, path, default)
    value = os.environ.get(env_var_name, value)
    if value is None:
        if required:
            logger.error(f'{env_var_name} env var or {path} in config file option is required!')
            sys.exit(1)
    else:
        value = convert_to(value)

    return value

class Address():
    def __init__(self, address_dict, env_prefix):
        self._host = prioritized_config(address_dict, 'host', f'{env_prefix}_HOST', required=True)
        self._port = prioritized_config(address_dict, 'port', f'{env_prefix}_PORT', required=True)
    def get_host(self):
        return self._host
    def get_port(self):
        return int(self._port)
    def get_address(self):
        return f'{self._host}:{self._port}'

class Video():
    def __init__(self, video_dict, env_prefix):
        self._enable = prioritized_config(video_dict, 'enable', f'{env_prefix}_ENABLE', convert_to=bool, required=True)
        if self._enable:
            # NOTE: When output the URI is not required even if video is enabled.
            #       By default goes to the default video output (screen)
            self._uri = prioritized_config(video_dict, 'uri', f'{env_prefix}_URI', required=False)
            if self._uri == 'screen':
                # To reproduce videos locally directly on the screen
                self._protocol = 'screen'
                self._location = 'screen'
            elif self._uri == 'v4l2':
                # When reading streams from v4l2 devices like webcams and tv cards
                self._protocol = 'v4l2'
                self._location = 'v4l2'
            else:
                try:
                    uri_split = self._uri.split('://')
                    self._protocol = uri_split[0]
                    self._location = uri_split[1]
                except:
                    logger.error(f'Wrong or missing video URI config! Ensure it starts with the protocol. Example: "file://", "https://", etc')
                    sys.exit(1)
        else:
            self._uri = None
            self._protocol = None
            self._location = None

    def is_enabled(self):
        return self._enable
    def get_uri(self):
        return self._uri
    def get_uri_protocol(self):
        return self._protocol
    def get_uri_location(self):
        return self._location

class Input():
    def __init__(self, input_dict):
        self._video = Video(input_dict['video'], f'{ENV_PREFIX}_INPUT_VIDEO')
        # Address where the output component is running
        self._address = Address(input_dict['address'], f'{ENV_PREFIX}_INPUT_ADDRESS')

    def get_video(self):
        return self._video
    def get_address(self):
        return self._address

class Output():
    def __init__(self, output_dict):
        self._video = Video(output_dict['video'], f'{ENV_PREFIX}_OUTPUT_VIDEO')
        if self._video.is_enabled():
            # Address where the output component is running
            self._address = Address(output_dict['address'], f'{ENV_PREFIX}_OUTPUT_ADDRESS')
            self._recv_buffer_size = prioritized_config(
                output_dict, 'recv_buffer_size',
                f'{ENV_PREFIX}_OUTPUT_RECV_BUFFER_SIZE', convert_to=int,
                default=300) # 5 seconds of 60 pfs video

    def get_video(self):
        return self._video
    def get_address(self):
        return self._address
    def get_recv_buffer_size(self):
        return self._recv_buffer_size

class Worker():
    def __init__(self, worker_dict):
        self._n_workers = prioritized_config(worker_dict, 'n_workers', f'{ENV_PREFIX}_WORKER_N_WORKERS', convert_to=int, required=True)
        self._recv_buffer_size = prioritized_config(
            worker_dict, 'recv_buffer_size',
            f'{ENV_PREFIX}_WORKER_RECV_BUFFER_SIZE', convert_to=int,
            default=300) # 5 seconds of 60 pfs video

    def get_n_workers(self):
        return self._n_workers
    def get_recv_buffer_size(self):
        return self._recv_buffer_size

class Plugins():
    def __init__(self, plugins_dict):
        self._dir = prioritized_config(plugins_dict, 'dir', f'{ENV_PREFIX}_PLUGINS_DIR', default='plugins')
        order = prioritized_config(plugins_dict, 'order', f'{ENV_PREFIX}_PLUGINS_ORDER', default='')
        self._order = tuple(re.split(r'[;,|]', order)) if order else ()

    def get_plugins_dir(self):
        return self._dir
    def get_plugins_order(self):
        return self._order

class Config(metaclass=Singleton):
    def __init__(self, config):
        logger.debug('Parsing configuration')
        self._log_level = prioritized_config(config, 'log_level', f'{ENV_PREFIX}_LOG_LEVEL', required=True)
        if not self._log_level == 'INFO' and not self._log_level == 'DEBUG' and not self._log_level == 'WARN':
            logger.warning(f'Unrecognized log level: {self._log_level}. Must be INFO, WARN or DEBUG. Falling back to DEBUG')
            self._log_level = 'DEBUG' # Changing this requires to change the default value in logger too.

        # TODO: we are assuming there is always a config file with all the sections, but a user could use just env vars
        plugins_section = dict.get(config, "plugins", {})
        self._plugins = Plugins(plugins_section)
        self._input = Input(config['input'])
        self._output = Output(config['output'])
        self._worker = Worker(config['worker'])

        logger.debug('[green]Configuration parsed[/green]')

    def get_input(self):
        return self._input
    def get_output(self):
        return self._output
    def get_worker(self):
        return self._worker
    def get_log_level(self):
        return self._log_level
    def get_plugins(self):
        return self._plugins
