use std::{sync::Arc, fmt};
use log::error;
use tokio::sync::Mutex;

use crate as pipeless;

#[derive(Clone,Copy,PartialEq)]
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
}

#[derive(Clone)]
pub struct StatelessHook {
    h_type: HookType,
    h_body: Arc<dyn HookTrait>,
}
impl StatelessHook {
    fn get_hook_type(&self) -> HookType {
        self.h_type
    }
    fn get_hook_body(&self) -> Arc<dyn HookTrait> {
        self.h_body.clone()
    }
}
#[derive(Clone)]
pub struct StatefulHook {
    h_type: HookType,
    h_body: Arc<Mutex<dyn HookTrait>>,
}
impl StatefulHook {
    fn get_hook_type(&self) -> HookType {
        self.h_type
    }
    fn get_hook_body(&self) -> Arc<Mutex<dyn HookTrait>> {
        self.h_body.clone()
    }
}

/// Pipeless hooks are the minimal executable unit
/// Stateless hooks can be used by many threads at the same time without issues, they could even be cloned,
/// since they usually contain, for example, simple Python modules.
/// Stateful hooks cannot be cloned, thus, they require to lock the hook, avoiding corrupting the state.
/// The execution of a stage that contains stateful hooks is slower than one based on just stateless hooks.
/// This is because when a stateful hook is executed for a frame, the rest of frames are waiting for the lock to be released,
/// however, in the stateless case, we can safely access the content of the hook from many frames at the same time.
/// Note Stateless hooks use Arc while Stateful use Arc_Mutex
#[derive(Clone)] // Cloning will not duplicate data since we are using Arc
pub enum Hook {
    StatelessHook(StatelessHook),
    StatefulHook(StatefulHook),
}
unsafe impl std::marker::Sync for Hook {}
unsafe impl std::marker::Send for Hook {}
impl Hook {
    pub fn new_stateless(hook_type: HookType, hook_body: Arc<dyn HookTrait>) -> Self {
        let hook = StatelessHook {
            h_type: hook_type,
            h_body: hook_body,
        };
        Self::StatelessHook(hook)
    }
    pub fn new_stateful(hook_type: HookType, hook_body: Arc<Mutex<dyn HookTrait>>) -> Self {
        let hook = StatefulHook {
            h_type: hook_type,
            h_body: hook_body,
        };
        Self::StatefulHook(hook)
    }

    pub async fn exec_hook(
        &self,
        frame: pipeless::data::Frame,
        stage_context: Arc<pipeless::stages::stage::Context>,
    ) -> std::option::Option<pipeless::data::Frame> {
        match self {
            Hook::StatelessHook(hook) => {
                // Offload the hook execution which is usually a CPU bounded (and intensive) task
                // out of the tokio thread pool
                // We use rayon because it uses a pool equal to the cores, which allows to process the optimal number of frames at once.
                let (send, recv) = tokio::sync::oneshot::channel();
                rayon::spawn({
                    let stage_context = stage_context.clone();
                    let hook = hook.clone();
                    move || {
                        let f = hook.get_hook_body().exec_hook(frame, &stage_context);
                        // Send the result back to Tokio.
                        let _ = send.send(f);
                    }
                });
                // Wait for the rayon task.
                let worker_res = recv.await;
                match worker_res {
                    Ok(f) => {
                        return f;
                    },
                    Err(err) => {
                        error!("Error pulling results from rayon worker: {}", err);
                        return None;
                    }
                }
            },
            // TODO: offload also on this function
            Hook::StatefulHook(hook) => {
                let h_body = hook.get_hook_body();
                let locked_hook = h_body.lock().await;
                locked_hook.exec_hook(frame, &stage_context)
            },
        }
    }

    pub fn get_hook_type(&self) -> HookType {
        match self {
            Hook::StatelessHook(hook) => {
                hook.get_hook_type()
            },
            Hook::StatefulHook(hook) => {
                hook.get_hook_type()
            },
        }
    }
}
