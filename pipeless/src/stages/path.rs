use std::{collections::HashMap, fmt};
use log::warn;
use serde_derive::{Serialize, Deserialize};

use crate as pipeless;

/// The frame path is the ordered list of stages names through which a frame have to pass.
#[derive(
    Clone,Debug,Serialize,Deserialize,PartialEq
)]
pub struct FramePath {
    path: Vec<String>,
}
impl FramePath {
    /// Receives a string with the stages list separated by slashes.
    /// Returns a Result with the framepath or with an error when the path is invalid
    pub fn new(path: &str, frame_path_executor: &FramePathExecutor) -> Result<Self, String> {
        let stages_names: Vec<String> =
            path.trim().split("/").map(|s| s.to_string()).collect();

        let frame_path = Self {
            path: stages_names
        };

        frame_path_executor.check_path(frame_path)
    }

    fn get_path(&self) -> &Vec<String> {
        &self.path
    }
}
// Allow to_string in frame_path
impl fmt::Display for FramePath {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}", self.path.join("/"))
    }
}

/// The same FramePathExecutor instance is created when pipeless is called
/// and the same instance is used by all pipelines and streams.
/// It maintains an instance of each user defined stage.
pub struct FramePathExecutor {
    stages: HashMap<String, pipeless::stages::stage::Stage>,
}
impl FramePathExecutor {
    pub fn new(stages_dir: &str) -> Self {
        Self {
            stages: pipeless::stages::parser::load_stages(stages_dir)
        }
    }

    /// Execute the provided frame path over the provided frame
    /// We execute the framepath for several frames at the same time, but obviously, for each
    /// frame the frampath goes in order.
    pub async fn execute_path(
        &self,
        frame: pipeless::frame::Frame,
        path: FramePath
    ) -> Option<pipeless::frame::Frame> {
        let mut frame = Some(frame);
        for stage_name in path.get_path().iter() {
            if let Some(stage) = self.stages.get(stage_name) {
                let stage_hooks = stage.get_hooks();

                // FIXME: we have the code duplicated per hook type just to match the hook type to guarantee the hooks order

                let pre_process_hook = find_hook(stage_hooks,  pipeless::stages::hook::HookType::PreProcess);
                if let Some(hook) = pre_process_hook {
                   frame = run_hook(&hook, stage, frame).await;
                }

                let process_hook = find_hook(stage_hooks,  pipeless::stages::hook::HookType::Process);
                if let Some(hook) = process_hook {
                    frame = run_hook(&hook, stage, frame).await;
                }

                let post_process_hook = find_hook(stage_hooks,  pipeless::stages::hook::HookType::PostProcess);
                if let Some(hook) = post_process_hook {
                    frame = run_hook(&hook, stage, frame).await;
                }
            } else {
                warn!("Stage '{}' not found, skipping execution", stage_name);
            }
        }

        frame
    }

    /// Validates if all the stages of a frame path exist
    fn check_path(&self, frame_path: FramePath) -> Result<FramePath, String> {
        if let Some(not_found) = frame_path.get_path().iter().find(|s| !self.stages.contains_key(*s)) {
            Err(format!("{} stage does not exist", not_found))
        } else {
            Ok(frame_path)
        }
    }
}

async fn run_hook(
    hook: &pipeless::stages::hook::Hook,
    stage: &pipeless::stages::stage::Stage,
    frame: Option<pipeless::frame::Frame>,
) -> Option<pipeless::frame::Frame> {
    if let Some(frame) = frame {
        let context = stage.get_context();
        return hook.exec_hook(frame, context).await;
    }

    None
}

fn find_hook(
    stage_hooks: &Vec<super::hook::Hook>,
    search_type: pipeless::stages::hook::HookType,
) -> Option<pipeless::stages::hook::Hook> {
    for h in stage_hooks {
        let h_type = h.get_hook_type();
        if h_type == search_type {
            return Some(h.clone());
        }
    }
    None
}
