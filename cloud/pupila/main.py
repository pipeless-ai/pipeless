import os

from lib.input import input
from lib.logger import logger

def main ():
    """
    Entrypoint for all components.
    Each component is executed depending on the provided flags
    """
    # TODO: handle flags for input, worker, output
    # TODO: join config file and env vars (priority to env vars) and build config object to pass to components
    input_video_uri =  os.environ.get('INPUT_VIDEO_URI')
    if input_video_uri is None:
        raise 'Missing input video URI!'

    config = {
        'input': {
            'video': {
                'uri': input_video_uri
            }
        },
        "test_mode": bool(os.environ.get('TEST_MODE', False)),
    }

    logger.info(f"Reading video from {config['input']['video']['uri']}")

    input.input(config)

if __name__ == "__main__":
    main()
