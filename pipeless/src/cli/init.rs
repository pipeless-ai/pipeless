use std::env;
use std::fs::{self, File};
use std::io::prelude::*;

use crate::cli::stage::generate_stage;

use super::stage::ask_for_new_stage;

pub fn init(project_name: &str, template: &Option<String>) {
    fs::create_dir(project_name).unwrap();
    // TODO: init a git repository inside the project root
    match template {
        Some(template_name) => {
            match template_name.as_str() {
                "empty" => {},
                "scaffold" => {
                    let stage_path = &format!("{}/my-stage", project_name);
                    fs::create_dir(stage_path).unwrap();

                    let file_names = ["pre-process.py", "process.py", "post-process.py"];
                    for file_name in &file_names {
                        let file_path = format!("{}/{}", stage_path, file_name);
                        let mut file = File::create(&file_path).unwrap();

                        let file_content = "def hook(frame_data, context):
                    frame = frame_data['modified'] # Using 'modified' to propagate changes from possible previous stages in the frame execution path
                    # Do something to the frame here
                    # ...

                    # If you did not modify the frame in place update it
                    frame_data['modified'] = frame";

                        file.write_all(file_content.as_bytes()).unwrap();
                    }
                },
                unknown_template => {
                    println!("❌ Unknown template provided: {}", unknown_template);
                    return;
                }
            }
        },
        None => {
            // Use the interactive creation
            if let Err(err) = env::set_current_dir(&project_name) {
                eprintln!("Cannot move into the new project directory, skipping interactive creation. Error: {}", err);
            } else {
                while match ask_for_new_stage() {
                    Ok(b) => b,
                    Err(err) =>  {
                        println!("❌ Failed to initialize stage interactively: {}", err);
                        false
                    }
                } {
                    generate_stage();
                }
            }
        }
    }
    println!("✅ New project created at: {}", project_name);
}
