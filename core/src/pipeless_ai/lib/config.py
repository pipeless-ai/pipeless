import os
import re
import sys

from pipeless_ai.lib.singleton import Singleton
from pipeless_ai.lib.logger import logger

ENV_PREFIX = 'PIPELESS'

def get_section_from_dict(_dict: dict, prop: str):
    """
    Securely parse a section from a dict returning.
    Returns an empty dict if the value is None or is no specified
    """
    return _dict.get(prop) or {}

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
                except Exception:
                    logger.error(
                        'Wrong or missing video URI config! Ensure it starts with the protocol. Example: "file://", "https://", etc'
                    )
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
        self._video = Video(get_section_from_dict(input_dict, 'video'), f'{ENV_PREFIX}_INPUT_VIDEO')
        # Address where the output component is running
        self._address = Address(get_section_from_dict(input_dict, 'address'), f'{ENV_PREFIX}_INPUT_ADDRESS')

    def get_video(self):
        return self._video
    def get_address(self):
        return self._address

class Output():
    def __init__(self, output_dict):
        self._video = Video(get_section_from_dict(output_dict, 'video'), f'{ENV_PREFIX}_OUTPUT_VIDEO')
        if self._video.is_enabled():
            # Address where the output component is running
            self._address = Address(get_section_from_dict(output_dict, 'address'), f'{ENV_PREFIX}_OUTPUT_ADDRESS')
            self._recv_buffer_size = prioritized_config(
                output_dict, 'recv_buffer_size',
                f'{ENV_PREFIX}_OUTPUT_RECV_BUFFER_SIZE', convert_to=int,
                default=300) # 5 seconds of 60 pfs video
            if self._recv_buffer_size > 8192:
                # This is a limitation of Pynng. Not documented, but it fails with higher numbers
                logger.error("The buffer size can't be higher than 8192")
                sys.exit(1)

    def get_video(self):
        return self._video
    def get_address(self):
        return self._address
    def get_recv_buffer_size(self):
        return self._recv_buffer_size

def parse_transpose_order(format):
    """
    Parses the transpose order provided by the user
    """
    transpose_order = format.split(",")
    if len(transpose_order) != 3: raise ValueError("The worker.inference.image_shape_format parameter must contain 3 fields. Widht, Height and Channels")
    transpose_order = [s.strip().lower() for s in transpose_order]
    return transpose_order

class Inference():
    def __init__(self, inference_dict):
        self._model_uri = prioritized_config(inference_dict, 'model_uri', f'{ENV_PREFIX}_WORKER_INFERENCE_MODEL_URI')
        # It is a common practise to use a model to pre-process the input for the actual model.
        self._pre_process_model_uri = prioritized_config(inference_dict, 'pre_process_model_uri', f'{ENV_PREFIX}_WORKER_INFERENCE_PRE_PROCESS_MODEL_URI', default=None)
        # Force model versions conversion
        self._force_ir_version = prioritized_config(inference_dict, 'force_ir_version', f'{ENV_PREFIX}_WORKER_INFERENCE_FORCE_IR_VERSION', default=None, convert_to=int)
        self._force_opset_version = prioritized_config(inference_dict, 'force_opset_version', f'{ENV_PREFIX}_WORKER_INFERENCE_FORCE_OPSET_VERSION', default=None, convert_to=int)
        # The expected image shape format of the model input to automatically transpose it
        self._image_shape_format = prioritized_config(inference_dict, 'image_shape_format', f'{ENV_PREFIX}_WORKER_INFERENCE_IMAGE_SHAPE_FORMAT', default=None)
        if self._image_shape_format:
            self._image_shape_format = parse_transpose_order(self._image_shape_format)
        # Allow thte user to force the image input size
        self._image_width = prioritized_config(inference_dict, 'image_width', f'{ENV_PREFIX}_WORKER_INFERENCE_IMAGE_WIDTH', default=None)
        self._image_height = prioritized_config(inference_dict, 'image_height', f'{ENV_PREFIX}_WORKER_INFERENCE_IMAGE_HEIGHT', default=None)
        self._image_channels = prioritized_config(inference_dict, 'image_channels', f'{ENV_PREFIX}_WORKER_INFERENCE_IMAGE_CHANNELS', default=None)

    def get_model_uri(self):
        return self._model_uri
    def get_pre_process_model_uri(self):
        return self._pre_process_model_uri
    def get_force_opset_version(self):
        return self._force_opset_version
    def get_force_ir_version(self):
        return self._force_ir_version
    def get_image_shape_format(self):
        return self._image_shape_format
    def get_image_width(self):
        return self._image_width
    def get_image_height(self):
        return self._image_height
    def get_image_channels(self):
        return self._image_channels

class Worker():
    def __init__(self, worker_dict):
        self._n_workers = prioritized_config(worker_dict, 'n_workers', f'{ENV_PREFIX}_WORKER_N_WORKERS', convert_to=int, required=True)
        self._recv_buffer_size = prioritized_config(
            worker_dict, 'recv_buffer_size',
            f'{ENV_PREFIX}_WORKER_RECV_BUFFER_SIZE', convert_to=int,
            default=300) # 5 seconds of 60 pfs video
        if self._recv_buffer_size > 8192:
            # This is a limitation of Pynng. Not documented, but it fails with higher numbers
            logger.error("The buffer size can't be higher than 8192")
            sys.exit(1)
        self._show_exec_time = prioritized_config(worker_dict, 'show_exec_time', f'{ENV_PREFIX}_WORKER_SHOW_EXEC_TIME', convert_to=bool, default=False)
        # Built in inference runtime configuration
        self._inference = Inference(worker_dict.get("inference") or {})
        # Allow the user to enable the line profiler for his code
        self._enable_profiler = prioritized_config(worker_dict, 'enable_profiler', f'{ENV_PREFIX}_WORKER_ENABLE_PROFILER', convert_to=bool, default=False)
    def get_n_workers(self):
        return self._n_workers
    def get_recv_buffer_size(self):
        return self._recv_buffer_size
    def get_show_exec_time(self):
        return self._show_exec_time
    def get_inference(self):
        return self._inference
    def get_enable_profiler(self):
        return self._enable_profiler

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
        if self._log_level not in ['INFO', 'DEBUG', 'WARN']:
            logger.warning(f'Unrecognized log level: {self._log_level}. Must be INFO, WARN or DEBUG. Falling back to DEBUG')
            self._log_level = 'DEBUG' # Changing this requires to change the default value in logger too.

        # TODO: we are assuming there is always a config file, but a user could use just env vars
        self._plugins = Plugins(get_section_from_dict(config, 'plugins'))
        self._input = Input(get_section_from_dict(config, 'input'))
        self._output = Output(get_section_from_dict(config, 'output'))
        self._worker = Worker(get_section_from_dict(config, 'worker'))

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
