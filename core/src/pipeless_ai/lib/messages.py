import pickle
from enum import Enum
import numpy as np

from pipeless_ai.lib.logger import logger

class MsgType(Enum):
    CAPABILITIES = 1
    RGB_IMAGE = 2
    EOS = 3 # End of streams
    TAGS = 4

class Msg():
    """
    General message type. To be inherited by every message type.
    """
    def serialize(self):
        pass
    def get_type(self):
        return self._type
    def get_data(self):
        return self._data

class StreamCapsMsg(Msg):
    """
    Indicates the format of a stream. Usually sent as the start of a stream
    """
    def __init__(self, capabilitites):
        self._type = MsgType.CAPABILITIES
        self._caps  = capabilitites
    def serialize(self):
        return pickle.dumps({
            "type": self._type,
            "caps": self._caps,
        })
    def get_caps(self):
        return self._caps

class StreamTagsMsg(Msg):
    """
    Contains the tags used to describe media metadata
    """
    def __init__(self, tags: str):
        self._type = MsgType.TAGS
        self._tags  = tags
    def serialize(self):
        return pickle.dumps({
            "type": self._type,
            "tags": self._tags,
        })
    def get_tags(self):
        return self._tags

class EndOfStreamMsg(Msg):
    """
    Indicates that the stream that was being sent ended
    """
    def __init__(self):
        self._type = MsgType.EOS
    def serialize(self):
        return pickle.dumps({
            "type": self._type,
        })

class RgbImageMsg(Msg):
    """
    Raw RGB image data and basic information
    """
    def __init__(self, width, height, raw_data, dts, pts, duration):
        self._type = MsgType.RGB_IMAGE
        self._dts = dts
        self._pts = pts
        self._duration = duration
        self._width = width
        self._height = height
        self._data = raw_data

    def serialize(self):
        s_data = self._data
        if isinstance(self._data, np.ndarray):
            s_data = self._data.dumps()
        return pickle.dumps({
            "type": self._type,
            "dts": self._dts,
            "pts": self._pts,
            "duration": self._duration,
            "width": self._width,
            "height": self._height,
            "data": s_data
        })

    def update_data(self, new_raw_data):
        """
        The data is updated in raw
        """
        self._data = new_raw_data

    def get_width(self):
        return self._width
    def get_height(self):
        return self._height
    def get_dts(self):
        return self._dts
    def get_pts(self):
        return self._pts
    def get_duration(self):
        return self._duration

def deserialize(_msg):
    """
    Take a serialized message and returns the proper message
    """
    msg = pickle.loads(_msg)
    if msg["type"] == MsgType.RGB_IMAGE:
        r_data = msg["data"]
        if isinstance(r_data, bytes):
            # Ref: https://numpy.org/doc/stable/reference/generated/numpy.ndarray.dumps.html#numpy.ndarray.dumps
            r_data = pickle.loads(msg["data"])

        return RgbImageMsg(
            msg["width"],
            msg["height"],
            r_data,
            msg["dts"],
            msg["pts"],
            msg["duration"],
        )
    elif msg["type"] == MsgType.CAPABILITIES:
        return StreamCapsMsg(msg["caps"])
    elif msg["type"] == MsgType.EOS:
        return EndOfStreamMsg()
    elif msg["type"] == MsgType.TAGS:
        return StreamTagsMsg(msg["tags"])
    else:
        logger.warning(f'Unknown message type: {msg["type"]}')
        return None
