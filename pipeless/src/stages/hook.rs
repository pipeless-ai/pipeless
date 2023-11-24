use std::{sync::Arc, fmt};
use tokio::sync::Mutex;

use crate as pipeless;

pub enum HookType {
    PreProcess,
    Process,
    PostProcess,
}
impl fmt::Display for HookType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", match self {
            HookType::PreProcess => "pre_process",
            HookType::Process => "process",
            HookType::PostProcess => "post_process",
        })
    }
}

// We have to add Send + Sync to be able to use spawn_blocking to call exec_hook
pub trait HookTrait: Send + Sync {
    fn exec_hook(
        &self,
        frame: pipeless::data::Frame,
        stage_context: &pipeless::stages::stage::Context
    ) -> Option<pipeless::data::Frame>;

    fn get_hook_type(&self) -> HookType;
}

/// Pipeless hooks are the minimal executable unit
/// Stateless hooks can be used by many threads at the same time without issues, they could even be cloned,
/// since they usually contain, for example, simple Python modules.
/// Stateful hooks cannot be cloned, thus, they require to lock the hook, avoiding corrupting the state.
/// The execution of a stage that contains stateful hooks is slower than one based on just stateless hooks.
/// This is because when a stateful hook is executed for a frame, the rest of frames are waiting for the lock to be released,
/// however, in the stateless case, we can safely access the content of the hook from many frames at the same time.
#[derive(Clone)] // Cloning will not duplicate data since we are using Arc
pub enum Hook {
    StatelessHook(Arc<dyn HookTrait>),
    StatefulHook(Arc<Mutex<dyn HookTrait>>),
}
unsafe impl std::marker::Sync for Hook {}
unsafe impl std::marker::Send for Hook {}
impl Hook {
    pub fn new_stateless(arc_hook: Arc<dyn HookTrait>) -> Self {
        Self::StatelessHook(arc_hook)
    }
    pub fn new_stateful(mutex_hook: Arc<Mutex<dyn HookTrait>>) -> Self {
        Self::StatefulHook(mutex_hook)
    }

    pub async fn exec_hook(
        &self,
        frame: pipeless::data::Frame,
        stage_context: &pipeless::stages::stage::Context,
    ) -> std::option::Option<pipeless::data::Frame> {
        match self {
            Hook::StatelessHook(hook) => {
                hook.exec_hook(frame, stage_context)
            },
            Hook::StatefulHook(hook) => {
                let locked_hook = hook.lock().await;
                locked_hook.exec_hook(frame, stage_context)
            },
        }
    }

    pub async fn get_hook_type(&self) -> HookType {
        match self {
            Hook::StatelessHook(hook) => {
                hook.get_hook_type()
            },
            Hook::StatefulHook(hook) => {
                let locked_hook = hook.lock().await;
                let h_type = locked_hook.get_hook_type();
                h_type
            },
        }
    }
}