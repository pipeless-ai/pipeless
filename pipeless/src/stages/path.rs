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
    /// Since there is not async code here, once a stage starts to execute
    /// for a frame, it doesn't stop until te stage finishes (after post-process)
    /// TODO: we should add async code here to pass the CPU when moving frames to/from the GPU
    pub fn execute_path(
        &self,
        frame: pipeless::data::Frame,
        path: FramePath
    ) -> Option<pipeless::data::Frame> {
        let mut frame = Some(frame);
        for stage_name in path.get_path().iter() {
            if let Some(stage) = self.stages.get(stage_name) {
                let stage_hooks = stage.get_hooks();

                // FIXME: we have the code duplicated per hook type just to match the hook type to guarantee the hooks order

                let pre_process_hook = stage_hooks.iter().find(|h| matches!(h, pipeless::stages::hook::Hook::PreProcessHook(_)));
                if let Some(hook) = pre_process_hook {
                    let context = stage.get_context();
                    if let Some(f) = frame {
                        frame = hook.get_hook_def().exec_hook(f, &context);
                    }
                }

                let process_hook = stage_hooks.iter().find(|h| matches!(h, pipeless::stages::hook::Hook::ProcessHook(_)));
                if let Some(hook) = process_hook {
                    let context = stage.get_context();
                    if let Some(f) = frame {
                        frame = hook.get_hook_def().exec_hook(f, &context);
                    }
                }

                let post_process_hook = stage_hooks.iter().find(|h| matches!(h, pipeless::stages::hook::Hook::PostProcessHook(_)));
                if let Some(hook) = post_process_hook {
                    let context = stage.get_context();
                    if let Some(f) = frame {
                        frame = hook.get_hook_def().exec_hook(f, &context);
                    }
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