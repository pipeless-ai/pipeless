use std::{fs::{self, File}, io::Write};

use inquire::{InquireError, Select, Text, Confirm};

use super::stage::get_stages_names;

fn get_language_extension(language: &str) -> String {
    match language {
        "Python" => String::from("py"),
        _ => {
            unreachable!();
        }
    }
}

/// Receives the hook without extension
fn hook_exists_in_stage(stage: &str, hook_file_name: &str) -> bool {
    let mut entries = fs::read_dir(stage).unwrap();
    // Check if any file within the stage (ignoring the language extension) exists
    entries.any(|entry| {
        if let Ok(entry) = entry {
            let entry_name = entry.file_name();
            if let Some(entry_str) = entry_name.to_str() {
                entry_str.starts_with(hook_file_name)
            } else {
                false
            }
        } else {
            false
        }
    })
}

fn create_python_hook(stage: &str, hook_file_name: &str) {
    let file_path = format!("{}/{}", stage, hook_file_name);

    let content = "def hook(frame_data, context):
    print(\"Hello Pipeless\")
";

    let mut file = File::create(file_path).unwrap();
    file.write_all(content.as_bytes()).unwrap();
}


fn ask_for_hook_language() -> Result<&'static str, InquireError> {
    let languages = vec![
        "Python",
    ];
    Select::new("Select the programming language for the hook:", languages).prompt()
}

fn ask_for_inference_runtime() -> Result<&'static str, InquireError> {
    let runtimes = vec![
        "onnx",
    ];
    Select::new("Select the inference runtime you would like to use:", runtimes).prompt()
}

fn ask_for_model_uri() -> Result<String, InquireError> {
    Text::new("Please provide the URI to fetch the model:")
        .with_help_message("When using files should start by `file://`. You can also use http or https.")
        .prompt()
}

fn ask_for_hook_type() -> Result<&'static str, InquireError> {
    let hook_types = vec![
        "pre-process",
        "process",
        "post-process",
    ];

    Select::new("Select the inference runtime you would like to use:", hook_types).prompt()
}

fn generate_json_process_hook(stage: &str) -> Result<(), InquireError> {
    let file_path = format!("{}/{}", stage, "process.json");

    let inference_runtime = ask_for_inference_runtime()?;
    let model_uri = ask_for_model_uri()?;

    let content = format!("{{
    \"runtime\": \"{}\",
    \"model_uri\": \"{}\",
    \"inference_params\": {{ }}
}}", inference_runtime, model_uri);

    let mut file = File::create(file_path).unwrap();
    file.write_all(content.as_bytes()).unwrap();

    Ok(())
}

pub fn generate_hook(stage: Option<String>, hook_type: Option<String>) -> Result<(), InquireError> {
    let stage_name = match stage {
        Some(s) => s,
        None => ask_for_target_stage()?,
    };

    let hook_type = match hook_type {
        Some(t) => t,
        None => ask_for_hook_type()?.to_owned(),
    };

    if hook_type == "process" {
        let use_json = Confirm::new("Do you want to use one of the inference runtimes?")
            .with_default(true)
            .with_help_message("You can either use an inference runtime that will automatically load your model or write custom processing logic.")
            .prompt()?;

        if use_json {
            generate_json_process_hook(&stage_name)?;
        } else {
            generate_common_hook(&stage_name, &hook_type)?;
        }
    } else {
        generate_common_hook(&stage_name, &hook_type)?;
    }

    Ok(())
}

fn generate_common_hook(stage: &str, hook_type: &str) -> Result<(), InquireError> {
    let language = ask_for_hook_language()?;

    if hook_exists_in_stage(&stage, hook_type) {
        println!("❌ There is already a {} hook in the stage.", hook_type);
    } else {
       let hook_file_name = &format!("{}.{}", hook_type, get_language_extension(language));
       create_python_hook(&stage, hook_file_name);
    }

    Ok(())
}

fn ask_for_target_stage() -> Result<String, InquireError> {
    let existing_stages = get_stages_names();
    // Ask for the stage name where the hook should be created
    let stage_name = Select::new("Select the stage to add this hook to:", existing_stages).prompt()?;
    Ok(stage_name)
}

pub fn generate_hook_wrapper() {
    match generate_hook(None, None) {
        Ok(_) => println!("\n✅ The stage has been created\n"),
        Err(err) => println!("❌ Failed to generate the hook: {}", err)
    }
}