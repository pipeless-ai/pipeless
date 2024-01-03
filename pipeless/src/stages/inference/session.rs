use std::str::FromStr;

use log::warn;

use crate as pipeless;

use super::{
    onnx::{OnnxSession, OnnxSessionParams},
    openvino::{OpenvinoSession, OpenvinoSessionParams},
    roboflow::{RoboflowSession, RoboflowSessionParams}
};

pub trait SessionTrait {
    fn infer(&self, frame: pipeless::frame::Frame) -> pipeless::frame::Frame;
}

pub enum InferenceSession {
    Onnx(OnnxSession),
    Openvino(OpenvinoSession),
    Roboflow(RoboflowSession),
}
impl InferenceSession {
    pub fn infer(&self, frame: pipeless::frame::Frame) -> pipeless::frame::Frame {
        match self {
            InferenceSession::Onnx(onnx_session) => onnx_session.infer(frame),
            InferenceSession::Roboflow(roboflow_session) => roboflow_session.infer(frame),
            InferenceSession::Openvino(_) => unimplemented!(),
        }
    }
}

pub enum SessionParams {
    Onnx(OnnxSessionParams),
    Openvino(OpenvinoSessionParams),
    Roboflow(RoboflowSessionParams),
}
impl SessionParams {
    pub fn from_raw_data(stage_name: &str, runtime: &super::runtime::InferenceRuntime, data: &serde_json::Value) -> Self {
        match runtime {
            super::runtime::InferenceRuntime::Onnx => {
                let execution_provider = data["execution_provider"].as_str().unwrap_or_else(|| {
                    warn!("'execution_provider' not specified, defaulting to 'CPU'");
                    "cpu"
                });
                let execution_mode = data["execution_mode"].as_str();
                let inter_threads = data["inter_threads"].as_i64();
                if inter_threads.is_some() && execution_mode.is_none() {
                    warn!("'execution_mode' must be set to 'Parallel' for 'inter_threads' to take effect");
                }
                let intra_threads = data["intra_threads"].as_i64();
                SessionParams::Onnx(
                    OnnxSessionParams::new(
                        stage_name,
                        execution_provider, execution_mode,
                        inter_threads.map(|t| t as i16),
                        intra_threads.map(|t| t as i16)
                ))
            },
            super::runtime::InferenceRuntime::Openvino => unimplemented!(),
            super::runtime::InferenceRuntime::Roboflow => {
                let roboflow_model_id = data["roboflow_model_id"].as_str().unwrap_or_else(|| {
                    panic!("When using Roboflow inference the 'roboflow_model_id' inference parameter is required.");
                });
                if roboflow_model_id.split('/').collect::<Vec<&str>>().len() != 2 {
                    panic!("Wrong Roboflow model ID provided: {}. Ensure it follows the correct format. Example: 'soccer-players-5fuqs/1'", data["roboflow_model_id"]);
                }
                let inference_server_url = data["roboflow_inference_server_url"].as_str().unwrap_or_else(|| {
                    warn!("'roboflow_inference_server_url' not specified, defaulting to 'https://detect.roboflow.com'");
                    "https://detect.roboflow.com"
                });
                let task_type_str = data["roboflow_task_type"].as_str().unwrap_or_else(|| { "" });
                let task_type = super::roboflow::RoboflowTaskType::from_str(task_type_str)
                    .expect("The 'inference_params' field must include 'roboflow_task_type' as one of 'ObjectDetection', 'InstanceSegmentation', 'Classification', 'KeypointsDetection'");

                let request_timeout = data["roboflow_request_timeout"].as_i64().unwrap_or_else(|| {
                    warn!("'roboflow_request_timeout' not specified, defaulting to 2 seconds");
                    2000
                }) as u64;

                if let Ok(api_key) = std::env::var("PIPELESS_ROBOFLOW_API_KEY") {
                    SessionParams::Roboflow(
                        RoboflowSessionParams::new(
                            inference_server_url, roboflow_model_id,
                            &api_key, task_type, request_timeout
                        ))
                } else {
                    panic!("To use the Roboflow inference integration you need to export the env var PIPELESS_ROBOFLOW_API_KEY containing your Roboflow API key.");
                }
            },
        }
    }
}
