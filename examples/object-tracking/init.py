from norfair import Tracker

def init():
    return {
        "tracker": Tracker(distance_function="euclidean", distance_threshold=50)
    }
