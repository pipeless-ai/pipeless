use crate as pipeless;

use crate::stages::hook::HookTrait;
use super::{runtime::InferenceRuntime, session::{InferenceSession, SessionParams}};

/// Inference hooks maintain the inference session.
/// When created as stateless hooks, the inference session will be duplicated to every worker (hook function).
/// When using a model that maintains internal state a stateful hook should be used.
/// Since the hook is associated to a stage, the inference session will last as long as the stage
/// To use different sessions per stream, the stage should be duplicated. Creating a symlink
/// in the project folder is enough to split the inference session.
pub struct InferenceHook {
    session: InferenceSession,
}
impl InferenceHook {
    pub fn new(
        runtime: &InferenceRuntime,
        session_params: SessionParams,
        model_uri: &str
    ) -> Self {
        let session = match runtime {
            InferenceRuntime::Onnx =>  {
                let onnx_session_result = pipeless::stages::inference::onnx::OnnxSession::new(model_uri, session_params);
                match onnx_session_result {
                    Ok(onnx_session) => pipeless::stages::inference::session::InferenceSession::Onnx(onnx_session),
                    Err(err) => panic!("{}", err)
                }
            },
            InferenceRuntime::Roboflow =>  {
                let roboflow_session_result = pipeless::stages::inference::roboflow::RoboflowSession::new(session_params);
                match roboflow_session_result {
                    Ok(roboflow_session) => pipeless::stages::inference::session::InferenceSession::Roboflow(roboflow_session),
                    Err(err) => panic!("{}", err)
                }
            },
            InferenceRuntime::Openvino => pipeless::stages::inference::session::InferenceSession::Openvino(
                pipeless::stages::inference::openvino::OpenvinoSession::new(model_uri, session_params)
            ),
        };

        Self { session }
    }
}
impl HookTrait for InferenceHook {
    fn exec_hook(
        &self,
        frame: crate::data::Frame,
        _: &crate::stages::stage::Context
    ) -> Option<crate::data::Frame> {
       let out_frame = self.session.infer(frame);
       Some(out_frame)
    }
}
