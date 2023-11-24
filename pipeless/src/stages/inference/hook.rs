use crate as pipeless;

use crate::stages::hook::HookTrait;
use super::{runtime::InferenceRuntime, session::{InferenceSession, SessionParams}};

/// Pipeless hooks are stateless, expect for the inference hook, which
/// maintains the inference session. There are models that maintain internal state.
/// Since the hook is associated to a stage, it will last as long as the stage
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