import cv2
def hook(frame_data, context):
    # Get RG frame
    frame = frame_data['original']
    # Load model
    model = context["model"]
    # Run inference
    bboxes, keypoints = model.invoke_inference(frame)
    # Draw results
    for bbox in bboxes:
        cv2.rectangle(frame, (bbox[1], bbox[0]), (bbox[3], bbox[2]), (0, 255, 0), 2)
    for keypoint in keypoints:
        cv2.circle(frame, (keypoint[0], keypoint[1]), 5, (255, 0, 255), -1)
    # Update the output image
    frame_data['modified'] = frame
