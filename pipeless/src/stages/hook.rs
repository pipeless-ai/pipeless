use crate as pipeless;

pub trait HookTrait {
    fn exec_hook(
        &self,
        frame: pipeless::data::Frame,
        stage_context: &pipeless::stages::stage::Context
    ) -> Option<pipeless::data::Frame>;
}

/// Hook definitions per language. All of them have to implement the HookTrait
pub enum HookDef {
    PythonHook(pipeless::stages::languages::python::PythonHook),
    RustHook(pipeless::stages::languages::rust::RustHook),
    InferenceHook(pipeless::stages::inference::hook::InferenceHook), // Hook that runs inference on a model
}
impl HookDef {
    pub fn exec_hook(
        &self,
        frame: pipeless::data::Frame,
        stage_context: &pipeless::stages::stage::Context
    ) -> Option<pipeless::data::Frame> {
        let frame = match self {
            HookDef::PythonHook(hook) => hook.exec_hook(frame, stage_context),
            HookDef::RustHook(hook) => hook.exec_hook(frame, stage_context),
            HookDef::InferenceHook(hook) => hook.exec_hook(frame, stage_context),
        };

        frame
    }
}

/// Pipeless hooks are the minimal executable unit. Hooks are stateless.
pub enum Hook {
    PreProcessHook(HookDef),
    ProcessHook(HookDef),
    PostProcessHook(HookDef),
}
impl Hook {
    /// Unpack the Hook to return the contained HookDef no matter the variant
    pub fn get_hook_def(&self) -> &HookDef {
        match self {
            Hook::PreProcessHook(def)
            | Hook::ProcessHook(def)
            | Hook::PostProcessHook(def) => {
                def
            },
            _ => unreachable!(),
        }
    }
}