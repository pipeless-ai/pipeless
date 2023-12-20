use std::fs;

use inquire::{
    Confirm, InquireError, Text,
};

use super::hook::generate_hook;

/// Asuming the stages are the directories in the current dir returns the list of existing stage names
pub fn get_stages_names() -> Vec<String> {
    let entries = fs::read_dir(".").unwrap();
    let directory_names: Vec<String> = entries
        .filter_map(|entry| {
            entry.ok().and_then(|e| {
                if e.file_type().ok()?.is_dir() {
                    Some(e.file_name().into_string().ok()?)
                } else {
                    None
                }
            })
        })
        .collect();

    directory_names
}

pub fn ask_for_new_stage() -> Result<bool, InquireError> {
    Confirm::new("Do you want to add a stage?")
        .with_default(true)
        .with_help_message("This will help you creating the stage interactively")
        .prompt()
}

fn query_stage_name() -> Result<String, InquireError> {
    Text::new("Give a name for the stage:").prompt()
}

pub fn generate_stage() {
    let name_res = query_stage_name();
    if let Ok(name) = name_res {
        fs::create_dir(&name).unwrap();

        let create_preprocess = Confirm::new("Do you want to create a pre-process hook?")
            .with_default(true)
            .with_help_message("Pre-process hooks allow you to shape the data (frames) to match your model input format.")
            .prompt().unwrap();
        if create_preprocess {
            let res = generate_hook(Some(name.to_owned()), Some("pre-process".to_owned()));
            if let Err(err) = res {
                println!("❌ Failed to create the pre-process hook: {}", err);
            }
        }

        let create_process = Confirm::new("Do you want to create a process hook?")
            .with_default(true)
            .with_help_message("Process hooks are commonly used to run inference via models or to implement custom processing logic.")
            .prompt().unwrap();
        if create_process {
            let res = generate_hook(Some(name.to_owned()), Some("process".to_owned()));
            if let Err(err) = res {
                println!("❌ Failed to create the pre-process hook: {}", err);
            }
        }

        let create_postprocess = Confirm::new("Do you want to create a post-process hook?")
            .with_default(true)
            .with_help_message("Post-process hooks usually take the output of your model or processing logic to perform actions.")
            .prompt().unwrap();
        if create_postprocess {
            let res = generate_hook(Some(name.to_owned()), Some("post-process".to_owned()));
            if let Err(err) = res {
                println!("❌ Failed to create the post-process hook: {}", err);
            }
        }

        println!("\n✅ The stage has been created\n");
    } else {
        println!("❌ Failed to obtain the new stage name.");
    }
}
