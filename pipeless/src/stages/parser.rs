use std::{fs, path::PathBuf, collections::HashMap, sync::Arc};
use log::{warn, info, error};

use crate as pipeless;
use tokio;
use super::{stage::ContextTrait, hook::HookType};

fn for_each_dir_file<F>(dir_path: &str, mut func: F)
    where F: FnMut(&str, &PathBuf),
{
    let dir = fs::read_dir(dir_path)
        .expect(
            format!("Unable to read directory: {}",
            dir_path
        ).as_str());

    for entry in dir {
        let entry = entry.expect(
            format!("Error reading the directory: {}", dir_path
        ).as_str());
        let entry_path = entry.path();
        if let Some(entry_path_str) = entry_path.to_str() {
            func(entry_path_str, &entry_path);
        } else {
            warn!("Failed to get path as string, skipping.");
        }
    }
}

pub fn load_stages(dir_path: &str) -> HashMap<String, pipeless::stages::stage::Stage> {
    info!("⚙️  Loading stages from {}", dir_path);
    let mut stages = HashMap::<String, pipeless::stages::stage::Stage>::new();
    for_each_dir_file(dir_path, |path_str, path| {
        if path.is_file() {
            warn!("
                ⚠️  Ignoring file at stages root because it does not belong to any stage: {}.
                  Hint: Move it to a stage folder if this is not intentional
            ", path_str);
        } else {
            let stage_name;
            if let Some(dir_name) = path.file_name() {
                stage_name = dir_name.to_str().unwrap().replace("-", "_");
            } else {
                error!("⚠️  Could not get directory name from path: {}", path_str);
                return;
            }
            info!("⏳ Loading stage '{}' from {}", stage_name, path_str);
            let mut stage = pipeless::stages::stage::Stage::new(&stage_name);
            for_each_dir_file(path_str, |hook_path_str, hook_path| {
                info!("\tLoading hook from {}", hook_path_str);
                parse_hook(hook_path, &mut stage);
            });
            stages.insert(stage_name.to_string(), stage);
        }
    });

    stages
}

fn parse_hook(path: &PathBuf, stage: &mut pipeless::stages::stage::Stage) {
    if let Some(file_name) = path.file_name() {
        let hook_file_path = file_name.to_str()
            .expect("Unable to convert filename into string");
        let file_name_slice: Vec<&str> = hook_file_path.split(".").collect();
        let hook_type_str = file_name_slice[0];
        let extension = file_name_slice[1];

        let available_languages = pipeless::stages::languages::language::get_available_languages();
        let hook_language = available_languages
            .iter()
            .find(|ldef| ldef.get_extension() == extension);

        if let Some(hook_language) = hook_language {
            // TODO: should we read the hooks code or compiled languages and build it at runtime?
            //       or build the user application as a portable binary with the hooks embeeded?
            match fs::read_to_string(path) {
                Ok(hook_code) =>  {
                    if hook_type_str == "init" {
                        // TODO: Right now the context can be accessed only from hooks written in the same
                        //       language as the context.
                        //       One should be able to create init.py and access the context rom pre-process.js
                        //       A way of supporting it could be to export an interfafce from Rust to each language to
                        //       manipulate the context instead of passing the object from Rust to the hook language.
                        let stage_context =  build_context(stage.get_name(), hook_language, &hook_code);
                        stage.set_context(stage_context);
                    } else {
                        let hook;
                        if hook_type_str == "pre-process" || hook_type_str == "pre_process" {
                            hook = build_hook(
                                stage.get_name(),
                                hook_language,
                                pipeless::stages::hook::HookType::PreProcess,
                                &hook_code
                            );
                        } else if hook_type_str == "process" {
                            hook = build_hook(
                                stage.get_name(),
                                hook_language,
                                pipeless::stages::hook::HookType::Process,
                                &hook_code
                            );
                        } else if hook_type_str == "post-process" ||  hook_type_str == "post_process" {
                            hook = build_hook(
                                stage.get_name(),
                                hook_language,
                                pipeless::stages::hook::HookType::PostProcess,
                                &hook_code
                            );
                        } else {
                            warn!("Ignoring unsupported hook type: {}", hook_type_str);
                            return;
                        }
                        stage.add_hook(hook);
                    }
                },
                Err(err) => {
                    error!("Error reading hook file: {}", err);
                }
            }
        } else {
            warn!("File {} not loaded as a hook. Unsupported hook extension.", hook_file_path);
        }
    } else {
        error!("Unable to get file name from path");
    }
}

fn build_hook(
    stage_name: &str,
    lang: &pipeless::stages::languages::language::LanguageDef,
    hook_type: HookType,
    hook_code: &str,
) -> pipeless::stages::hook::Hook {
    match lang.get_language() {
        pipeless::stages::languages::language::Language::Python => {
            let py_hook = pipeless::stages::languages::python::PythonHook::new(
                hook_type, stage_name, hook_code
            );

            // The first line of the file can indicate if the hook must be stateful
            let mut is_stateful = false;
            if let Some(first_line) = hook_code.lines().next() {
                if first_line == "# make stateful" {
                    is_stateful = true;
                }
            } else {
                warn!("The hook is empty");
            }

            if is_stateful {
                info!("\t\tCreating stateful hook for {}-{}", stage_name, hook_type);
                pipeless::stages::hook::Hook::new_stateful(hook_type, Arc::new(tokio::sync::Mutex::new(py_hook)))
            } else {
                info!("\t\tCreating stateless hook for {}-{}", stage_name, hook_type);
                pipeless::stages::hook::Hook::new_stateless(hook_type, Arc::new(py_hook))
            }
        },
        pipeless::stages::languages::language::Language::Rust => { unimplemented!() },
        pipeless::stages::languages::language::Language::Json => {
            // Json files define hooks associated with inference sessions
            let inference_def: serde_json::Value = serde_json::from_str(hook_code)
                .expect(format!("Error parsing Json from hook '{}' of stage '{}'", hook_type, stage_name).as_str());
            let inference_runtime_key = &inference_def["runtime"];
            if !inference_runtime_key.is_string() {
                panic!("The json definition of the hook '{}' from the stage '{}' must include the field 'runtime' as a string", hook_type, stage_name);
            }
            let runtime = pipeless::stages::inference::runtime::InferenceRuntime::from_str(
                inference_runtime_key.as_str().unwrap()
            ).ok_or_else(|| {
                panic!("The provided inference runtime '{}' is not recognized. At hook '{}' of stage '{}'", inference_runtime_key, hook_type, stage_name);
            }).unwrap();

            let model_uri = &inference_def["model_uri"];
            if !model_uri.is_string() {
                panic!("The json definition of the hook '{}' from the stage '{}' must include the field 'model_uri' as a string", hook_type, stage_name);
            }

            let raw_session_params = &inference_def["inference_params"];
            if !raw_session_params.is_null() && !raw_session_params.is_object() {
                panic!("The json definition of the hook '{}' from the stage '{}' should include the field 'inference_params' as an object", hook_type, stage_name);
            }
            let session_params = pipeless::stages::inference::session::SessionParams::from_raw_data(stage_name, &runtime, raw_session_params);
            let inference_hook = pipeless::stages::inference::hook::InferenceHook::new(&runtime, session_params, model_uri.as_str().unwrap());

            let mut is_stateful = false;
            let make_stateful_v = &inference_def["make_stateful"];
            if !make_stateful_v.is_null() && !make_stateful_v.is_boolean() {
                panic!("The json definition of the hook '{}' from the stage '{}' should is wrong. The 'make_stateful' field must be a boolean", hook_type, stage_name);
            } else {
                if let Some(make_stateful) = make_stateful_v.as_bool() {
                    is_stateful = make_stateful
                }
            }

            if is_stateful {
                info!("\t\tCreating stateful hook for {}-{}", stage_name, hook_type);
                pipeless::stages::hook::Hook::new_stateful(hook_type, Arc::new(tokio::sync::Mutex::new(inference_hook)))
            } else {
                info!("\t\tCreating stateless hook for {}-{}", stage_name, hook_type);
                pipeless::stages::hook::Hook::new_stateless(hook_type, Arc::new(inference_hook))
            }
        },
    }
}

fn build_context(
    stage_name: &str,
    lang: &pipeless::stages::languages::language::LanguageDef,
    init_code: &str
) -> pipeless::stages::stage::Context {
    let stage_context =  match lang.get_language() {
        pipeless::stages::languages::language::Language::Python => pipeless::stages::stage::Context::PythonContext(
            pipeless::stages::languages::python::PythonStageContext::init_context(stage_name, init_code)
        ),
        pipeless::stages::languages::language::Language::Rust => pipeless::stages::stage::Context::RustContext(
            pipeless::stages::languages::rust::RustStageContext::init_context(stage_name, init_code),
        ),
        pipeless::stages::languages::language::Language::Json => {
            // init.json is not supported since Json hook files define inference sessions
            panic!("init.json is not supported. The context must be initialized in a programming language");
        },
    };
    stage_context
}
