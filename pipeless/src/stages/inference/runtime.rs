pub enum InferenceRuntime {
    Onnx,
    Openvino,
}
impl InferenceRuntime {
    pub fn from_str(runtime_str: &str) -> Option<Self> {
        if runtime_str == "onnx" {
            Some(InferenceRuntime::Onnx)
        } else if runtime_str == "openvino" {
            Some(InferenceRuntime::Openvino)
        } else {
            None
        }
    }
}