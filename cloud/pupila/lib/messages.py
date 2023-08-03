import pickle
from enum import Enum

class MsgType(Enum):
    METADATA = 1
    RGB_IMAGE = 2

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
    def update_data(self, data):
        self._data = data

class MetadataMsg(Msg):
    """
    Indicates the format of a stream
    """
    def __init__(self, width, height, raw_data):
        self._type = MsgType.METADATA
        self._data = raw_data
    
    def serialize(self):
        return pickle.dumps({
            "type": self._type,
            "data": self._data
        })

class RgbImageMsg(Msg):
    """
    Raw RGB image data and basic information
    """
    def __init__(self, width, height, raw_data, timestamp):
        self._type = MsgType.RGB_IMAGE
        self._timestamp = timestamp
        self._width = width
        self._height = height
        self._data = raw_data
    
    def serialize(self):
        return pickle.dumps({
            "type": self._type,
            "timestamp": self._timestamp,
            "width": self._width,
            "height": self._height,
            "data": self._data
        })
    
    def get_width(self):
        return self._width
    def get_height(self):
        return self._height
    def get_timestamp(self):
        return self._timestamp
    
def load_msg(msg: Msg):
    return pickle.loads(msg)
