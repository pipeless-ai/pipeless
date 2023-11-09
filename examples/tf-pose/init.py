from pipeless_ai_tf_models.multi_pose_estimation.lightning import MultiPoseEstimationLightning

def init():
    return {
        "model": MultiPoseEstimationLightning()
    }