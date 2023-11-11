use log::error;

use crate::{stages::{hook::HookTrait, stage::{Context, ContextTrait}}, data::Frame};

pub struct RustStageContext {
    // TODO
}
impl ContextTrait<RustStageContext> for RustStageContext {
    fn init_context(_stage_name: &str, _init_code: &str) -> RustStageContext {
        unimplemented!();
    }
}
pub struct RustHook {
    // TODO
}
impl HookTrait for RustHook {
    fn exec_hook(&self, frame: Frame, _stage_context: &Context) -> Option<Frame> {
        let frame = frame;
        if let crate::stages::stage::Context::RustContext(_stage_context) = _stage_context {
            unimplemented!();
        } else {
            error!("The stage context provided to the Rust executor is not a Rust context");
        }
        Some(frame)
    }
}