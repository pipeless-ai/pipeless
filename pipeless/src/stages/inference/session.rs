use log::warn;

use crate as pipeless;

use super::{
    onnx::{OnnxSession, OnnxSessionParams},
    openvino::{OpenvinoSession, OpenvinoSessionParams}
};

pub trait SessionTrait {
    fn infer(&self, frame: pipeless::data::Frame) -> pipeless::data::Frame;
}

pub enum InferenceSession {
    Onnx(OnnxSession),
    Openvino(OpenvinoSession)
}
impl InferenceSession {
    pub fn infer(&self, frame: pipeless::data::Frame) -> pipeless::data::Frame {
        match self {
            InferenceSession::Onnx(onnx_session) => onnx_session.infer(frame),
            InferenceSession::Openvino(_) => unimplemented!(),
        }
    }
}

pub enum SessionParams {
    Onnx(OnnxSessionParams),
    Openvino(OpenvinoSessionParams)
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
        }
    }
}
