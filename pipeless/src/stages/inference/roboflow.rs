use std::str::FromStr;
use base64::Engine;
use log::{warn, error};
use serde_derive::Deserialize;
use serde_json::json;
use crate as pipeless;

#[derive(Debug)]
pub struct RoboflowTaskTypeParseError;
pub enum RoboflowTaskType {
    ObjectDetection,
    InstanceSegmentation,
    Classification,
    KeypointsDetection,
}
impl RoboflowTaskType {
    fn to_str_endpoint(&self) -> &str {
        match self {
            // Serialize to the corresponding endpoint
            RoboflowTaskType::ObjectDetection => "infer/object_detection",
            RoboflowTaskType::InstanceSegmentation => "infer/instance_segmentation",
            RoboflowTaskType::Classification => "infer/classification",
            RoboflowTaskType::KeypointsDetection => "infer/keypoints_detection",
        }
    }
}
impl FromStr for RoboflowTaskType {
    type Err = RoboflowTaskTypeParseError;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "object_detection" | "ObjectDetection" | "objectDetection" | "OBJECT_DETECTION" | "OBJECTDETECTION" | "object-detection" | "Object-Detection"  => Ok(Self::ObjectDetection),
            "instance_segmentation" | "InstanceSegmentation" | "instanceSegmentation" | "INSTANCE_SEGMENTATION" | "INSTANCESEGMENTATION" | "instance-segmentation" | "Instance-Segmentation"  => Ok(Self::InstanceSegmentation),
            "classification" | "Classification" | "CLASSIFICATION" => Ok(Self::Classification),
            "keypoints_detection" | "KeypointsDetection" | "keypointsDetection" | "KEYPOINTS_DETECTION" | "KEYPOINTSDETECTION" | "keypoints-detection" | "Keypoints-Detection" => Ok(Self::KeypointsDetection),
            _ => Err(RoboflowTaskTypeParseError),
        }
    }
}

#[pyo3::pyclass]
#[derive(Deserialize,Clone)]
pub struct Point {
    x: f32,
    y: f32
}
#[pyo3::pymethods]
impl Point {
    pub fn get_x(&self) -> f32 {
        self.x
    }
    pub fn get_y(&self) -> f32 {
        self.y
    }
}

#[pyo3::pyclass]
#[derive(Deserialize,Clone)] // FIXME: we derive clone to be able to perform into_py for Python
pub struct RoboflowPredictions {
    x: f32,
    y: f32,
    width: f32,
    height: f32,
    class: String,
    class_id: i32,
    confidence: f32,
    class_confidence: Option<f32>,
    points: Option<Vec<Point>>,
}
#[pyo3::pymethods]
impl RoboflowPredictions {
    #[new]
    pub fn new(
        x: f32, y: f32, width: f32, height: f32,
        confidence: f32, class: String, class_id: i32, points: Option<Vec<Point>>,
        class_confidence: Option<f32>
    ) -> Self {
        Self { x, y, width, height, confidence, class, class_id, points, class_confidence }
    }
    pub fn get_x(&self) -> f32 {
        self.x
    }
    pub fn get_y(&self) -> f32 {
        self.y
    }
    pub fn get_width(&self) -> f32 {
        self.width
    }
    pub fn get_height(&self) -> f32 {
        self.height
    }
    pub fn get_confidence(&self) -> f32 {
        self.confidence
    }
    pub fn get_class(&self) -> String {
        self.class.clone()
    }
    pub fn get_class_id(&self) -> i32 {
        self.class_id
    }
    pub fn get_class_confidence(&self) -> Option<f32> {
        self.class_confidence
    }
    pub fn get_points(&self) -> Option<Vec<Point>> {
        self.points.clone()
    }
}

pub struct RoboflowSessionParams {
    inference_server_url: String, // URL where the Roboflow Inference server listens
    roboflow_model_id: String, // Id of the model in Roboflow universe
    api_key: String, // API key for the inference server,
    task_type: RoboflowTaskType,
    request_timeout: u64, // Number of milliseconds
}
impl RoboflowSessionParams {
    pub fn new(
        inference_server_url: &str,
        roboflow_model_id: &str,
        api_key: &str,
        task_type: RoboflowTaskType,
        request_timeout: u64,
    ) -> Self {
        Self {
            inference_server_url: inference_server_url.to_string(),
            roboflow_model_id: roboflow_model_id.to_string(),
            api_key: api_key.to_string(),
            task_type,
            request_timeout,
        }
    }
}
/// We provide a connection to an external Roboflow Inference server, thus, the session is a HTTP session
/// Note this will be shared by all hooks since is part of the inference stage
pub struct RoboflowSession {
    // Even though is not ideal, we can use the blocking client here because it will block only the current tokio thread where this code is being executed.
    http_session: reqwest::blocking::Client,
    params: RoboflowSessionParams,
}
impl RoboflowSession {
    pub fn new(params: super::session::SessionParams) -> Result<Self, String> {
        if let pipeless::stages::inference::session::SessionParams::Roboflow(roboflow_params) = params {
            let http_session = reqwest::blocking::Client::builder()
                .timeout(std::time::Duration::from_millis(roboflow_params.request_timeout))
                .pool_idle_timeout(None) // Keeps connections alive even when not used
                .pool_max_idle_per_host(15)
                .build()
                .expect("Error creating the HTTP for Roboflow inference");

            // We need the session params to infer via HTTP so we store them in the session
            Ok(Self { http_session, params: roboflow_params })
        } else {
            let err = "Wrong parameters provided to Roboflow Inference session";
            Err(err.to_owned())
        }
    }
}

impl super::session::SessionTrait for RoboflowSession {
    fn infer(&self, mut frame: pipeless::frame::Frame) -> pipeless::frame::Frame {
        let input_data = frame.get_inference_input().to_owned();
        if input_data.len() == 0 {
            warn!("No inference input data was provided. Did you forget to assign the 'inference_input' field to the frame data in your pre-process hook?");
            return frame;
        }

        // TODO: automatically resize and traspose the input image to the expected by the model. OR better, create a stage that does it so users simply have
        //       to use that stage before theirs

        // TODO: we should batch more than one frame to reduce the latency added on each network call
        let rgb_ndarray = input_data.view().to_owned(); // FIXME: This to_owned may add a copy of the data
        let rgb_image = ndarray_to_rgb_image(rgb_ndarray);
        match rgb_image {
            Some(image) => {
                let base64_frame = rgb_image_to_jpeg_base64(image);
                if self.params.inference_server_url.contains("roboflow.com") {
                    // For roboflow inference v0
                    let url = format!(
                        "{}/{}?api_key={}",
                        &self.params.inference_server_url,
                        &self.params.roboflow_model_id,
                        &self.params.api_key
                    );
                    let payload = base64_frame;

                    let response = self.http_session
                        .post(&url)
                        .header("Content-Type", "application/x-www-form-urlencoded")
                        .body(payload)
                        .send();

                    match response {
                        Ok(res) =>  {
                            let status = res.status();
                            if status.is_success() {
                                if let Ok(json_str) = res.text() {
                                    if let Ok(body) = serde_json::from_str::<serde_json::Value>(&json_str) {
                                        let predictions = &body["predictions"];
                                        if !predictions.is_null() {
                                            if let Ok(rob_inf_pred) = serde_json::from_value::<Vec<RoboflowPredictions>>(predictions.clone()) {
                                                frame.set_inference_output(pipeless::frame::InferenceOutput::RoboflowOutput(rob_inf_pred));
                                            } else {
                                                warn!("The was an error converting JSON to RoboflowPrediction object. Json value: {}", predictions);
                                            }
                                        }
                                    } else {
                                        error!("The response obtained from the Roboflow inference server cannot be converted into a JSON. Obtained: {}", json_str);
                                    }
                                } else {
                                    error!("The response from the Roboflow inference server cannot be converted into a string.");
                                }
                            } else {
                                error!("Error in request to Roboflow inference server. Status: {}", status);
                            }
                        },
                        Err(err) => { error!("Error querying the Roboflow inference server: {}", err); }
                    }
                } else {
                    // Roboflow inference v1
                    let url = format!("{}/{}", &self.params.inference_server_url, &self.params.task_type.to_str_endpoint());
                    let payload = json!({
                        "api_key": self.params.api_key,
                        "model_id": self.params.roboflow_model_id,
                        "image" : {
                            "type": "base64",
                            "value": base64_frame
                        },
                        "client_mode": "v1",
                    });
                    let response = self.http_session
                        .post(&url)
                        .header("Content-Type", "application/json")
                        .json(&payload)
                        .send();

                    match response {
                        Ok(res) =>  {
                            let status = res.status();
                            if status.is_success() {
                                if let Ok(json_str) = res.text() {
                                    if let Ok(body) = serde_json::from_str::<serde_json::Value>(&json_str) {
                                        let predictions = &body["predictions"];
                                        if !predictions.is_null() {
                                            if let Ok(rob_inf_pred) = serde_json::from_value::<Vec<RoboflowPredictions>>(predictions.clone()) {
                                                frame.set_inference_output(pipeless::frame::InferenceOutput::RoboflowOutput(rob_inf_pred));
                                            } else {
                                                warn!("The was an error converting JSON to RoboflowPrediction object. Json value: {}", predictions);
                                            }
                                        }
                                    } else {
                                        error!("The response obtained from the Roboflow inference server cannot be converted into a JSON. Obtained: {}", json_str);
                                    }
                                } else {
                                    error!("The response from the Roboflow inference server cannot be converted into a string.");
                                }
                            } else {
                                error!("Error in request to Roboflow inference server. Status: {}", status);
                            }
                        },
                        Err(err) => { error!("Error querying the Roboflow inference server: {}", err); }
                    }
                }
            },
            None => error!("Unable to convert frame array into rgb image, skipping frame.")
        }

        frame
    }
}

fn ndarray_to_rgb_image(arr: ndarray::ArrayBase<ndarray::OwnedRepr<f32>, ndarray::Dim<ndarray::IxDynImpl>>) -> Option<image::RgbImage> {
    let dims = arr.shape();
    let (height, width) = match dims.len() {
        1 => (dims[0], 1),       // 1D array
        2 => (dims[0], dims[1]),  // 2D array
        3 => (dims[0], dims[1]),  // 3D array
        _ => panic!("Unsupported number of dimensions"),
    };

    image::RgbImage::from_vec(
        width as u32,
        height as u32,
        arr.into_raw_vec().iter().map(|&x| x as u8).collect() // FIXME: this iteration to cast the elemnts to u8 from f32 is very slow
    )
}

fn rgb_image_to_jpeg_base64(img: image::RgbImage) -> String {
    let mut jpeg_data = Vec::new();
    let mut encoder = image::codecs::jpeg::JpegEncoder::new_with_quality(&mut jpeg_data, 90);
    encoder.encode_image(&img).unwrap();

    let mut buf = Vec::new();
    buf.resize(img.len() * 4 / 3 + 4, 0);

    let bytes_written = base64::engine::general_purpose::STANDARD.encode_slice(jpeg_data, &mut buf).unwrap();
    buf.truncate(bytes_written);

    let encoded_string = String::from_utf8(buf).expect("Invalid UTF-8");
    encoded_string
}

/* TODO: the following parameters are supported in the Robolow Python SDK,
         they can be passed to the Roboflow inference requests and we should allow to provide them
         in process.json.
struct KeypointsParameters {
    disable_preproc_auto_orientation: "disable_preproc_auto_orient,
    ("disable_preproc_contrast", "disable_preproc_contrast"),
    ("disable_preproc_grayscale", "disable_preproc_grayscale"),
    ("disable_preproc_static_crop", "disable_preproc_static_crop"),
    ("class_agnostic_nms", "class_agnostic_nms"),
    ("class_filter", "class_filter"),
    ("confidence_threshold", "confidence"),
    ("fix_batch_size", "fix_batch_size"),
    ("iou_threshold", "iou_threshold"),
    ("max_detections", "max_detections"),
    ("max_candidates", "max_candidates"),
    ("visualize_labels", "visualization_labels"),
    ("stroke_width", "visualization_stroke_width"),
    ("visualize_predictions", "visualize_predictions"),
}
fn to_keypoints_detection_parameters(params: ) -> Dict[str, Any]:
    let parameters = to_object_detection_parameters(params);
    parameters["keypoint_confidence"] = self.keypoint_confidence_threshold
return remove_empty_values(dictionary=parameters)

def to_object_detection_parameters(self) -> Dict[str, Any]:
parameters_specs = [
    ("disable_preproc_auto_orientation", "disable_preproc_auto_orient"),
    ("disable_preproc_contrast", "disable_preproc_contrast"),
    ("disable_preproc_grayscale", "disable_preproc_grayscale"),
    ("disable_preproc_static_crop", "disable_preproc_static_crop"),
    ("class_agnostic_nms", "class_agnostic_nms"),
    ("class_filter", "class_filter"),
    ("confidence_threshold", "confidence"),
    ("fix_batch_size", "fix_batch_size"),
    ("iou_threshold", "iou_threshold"),
    ("max_detections", "max_detections"),
    ("max_candidates", "max_candidates"),
    ("visualize_labels", "visualization_labels"),
    ("stroke_width", "visualization_stroke_width"),
    ("visualize_predictions", "visualize_predictions"),
]
return get_non_empty_attributes(
    source_object=self,
    specification=parameters_specs,
)

def to_instance_segmentation_parameters(self) -> Dict[str, Any]:
parameters = self.to_object_detection_parameters()
parameters_specs = [
    ("mask_decode_mode", "mask_decode_mode"),
    ("tradeoff_factor", "tradeoff_factor"),
]
for internal_name, external_name in parameters_specs:
    parameters[external_name] = getattr(self, internal_name)
return remove_empty_values(dictionary=parameters)

def to_classification_parameters(self) -> Dict[str, Any]:
parameters_specs = [
    ("disable_preproc_auto_orientation", "disable_preproc_auto_orient"),
    ("disable_preproc_contrast", "disable_preproc_contrast"),
    ("disable_preproc_grayscale", "disable_preproc_grayscale"),
    ("disable_preproc_static_crop", "disable_preproc_static_crop"),
    ("confidence_threshold", "confidence"),
    ("visualize_predictions", "visualize_predictions"),
    ("stroke_width", "visualization_stroke_width"),
]
return get_non_empty_attributes(
    source_object=self,
    specification=parameters_specs,
)*/
