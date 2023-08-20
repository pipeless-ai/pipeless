from lightning import MultiPoseEstimationLightning

mpe = MultiPoseEstimationLightning()

rgb_image =
result = mpe.invoke_inference(rgb_image)