use std::sync::Arc;
use log::error;

use crate as pipeless;

/// Stages can maintain a state that is global to the stage. We call it the stage context.
/// A user can define how to initialize this context in the init file of the stage and it is
/// provided to all the calls to the stage hooks.
/// This is usefull in many cases, for example, to maintain external connections
/// with analytics servers.
/// IMPORTANT: the context is global for the stage, which means it is global to all frame
/// of all streams.
// The context (like hooks) can be initialized by the user in several languages
// by returning data from the init function in the file init.{rs,py,...}
pub enum Context {
    EmptyContext,
    PythonContext(pipeless::stages::languages::python::PythonStageContext),
    RustContext(pipeless::stages::languages::rust::RustStageContext)
}
pub trait ContextTrait<T> {
    fn init_context(stage_name: &str, init_code: &str) -> T;
}

/// A Pipeless stage is the equivalent to a step that you would define when working
/// with traditional pipelines. Each stage has pre-process, process and post-process
/// phases.
/// Every of those phases as an associate hook that the user defines and is executed
/// for every frame given to the stage.
pub struct Stage {
    name: String,
    // A simple vector with all the hooks of this stage.
    // We don't care about the type allowing to add or remove types easily
    hooks: Vec<pipeless::stages::hook::Hook>,
    context: Arc<Context>,
}
impl Stage {
    pub fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            hooks: vec![],
            // Default empty stage context.
            // Arc because will be used among all frames in many threads
            context: Arc::new(Context::EmptyContext)
        }
    }

    pub fn get_name(&self) -> &str {
        &self.name
    }

    pub fn add_hook(&mut self, new_hook: pipeless::stages::hook::Hook) {
        if self.hooks.iter().any(|item| std::mem::discriminant(item) == std::mem::discriminant(&new_hook)) {
            error!("⚠️  Failed to add duplicated hook type to the stage '{}'.", self.name);
        } else {
            self.hooks.push(new_hook);
        }
    }

    pub fn get_hooks(&self) -> &[pipeless::stages::hook::Hook] {
        &self.hooks
    }

    pub fn set_context(&mut self, context: Context) {
        self.context = Arc::new(context);
    }

    pub fn get_context(&self) -> Arc<Context> {
        self.context.clone()
    }
}