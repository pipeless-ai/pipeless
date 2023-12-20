use std::str::FromStr;

use reqwest;
use serde_json::json;
use json_to_table;

fn handle_response(response: Result<reqwest::blocking::Response, reqwest::Error>) {
    match response {
        Ok(res) => {
            let status = res.status();
            let body = res.text().unwrap();
            if status.is_success() {
                println!("✅ {}", body);
            } else {
                println!("❌ Request to Pipeless node was not successful. Status code: {}", status);
                println!("👉 Error message: {}", body);
            }
        },
        Err(err) => {
            println!("❌ Failed to send request to Pipeless node.");
            println!("👉 Error message: {}", err.to_string());
        }
    }
}

pub fn add(
    input_uri: &str,
    output_uri: &Option<String>,
    frame_path: &str,
    restart_policy: &Option<String>,
) {
    let url = "http://localhost:3030/streams";

    let stages_vec: Vec<&str> = frame_path.split(",").collect();
    let payload = json!({
        "input_uri": input_uri,
        "output_uri": output_uri,
        "frame_path": stages_vec,
        "restart_policy": restart_policy,
    });

    let client = reqwest::blocking::Client::new();
    let response = client.post(url)
        .json(&payload)
        .send();

    handle_response(response);
}

pub fn remove(stream_id: &str) {
    let url = "http://localhost:3030/streams";

    let stream_uuid = uuid::Uuid::from_str(stream_id)
        .expect("Cannot convert provided stream_id into uuid");

    let delete_endpoint = format!("{}/{}", url, stream_uuid);

    let client = reqwest::blocking::Client::new();
    let response = client.delete(delete_endpoint)
        .send();

    handle_response(response);
}

pub fn update(
    stream_id: &str,
    input_uri: &Option<String>,
    output_uri: &Option<String>,
    frame_path: &Option<String>,
    restart_policy: &Option<String>,
) {
    let url = "http://localhost:3030/streams";

    let stream_uuid = uuid::Uuid::from_str(stream_id)
        .expect("Cannot convert provided stream_id into uuid");

    let update_endpoint = format!("{}/{}", url, stream_uuid);

    let stages_vec: Vec<&str> = match frame_path {
        Some(path) => path.split(",").collect(),
        None => vec![]
    };

    let payload = json!({
        "input_uri": input_uri,
        "output_uri": output_uri,
        "frame_path": stages_vec,
        "restart_policy": restart_policy,
    });

    let client = reqwest::blocking::Client::new();
    let response = client.put(update_endpoint)
        .json(&payload)
        .send();

    handle_response(response);
}

pub fn list() {
    let url = "http://localhost:3030/streams";

    let client = reqwest::blocking::Client::new();
    let response = client.get(url)
        .send();

    match response {
        Ok(res) => {
            let status = res.status();
            let body = res.text().unwrap();
            if status.is_success() {
                let body_json = serde_json::from_str(body.as_str()).unwrap();
                let mut table = json_to_table::json_to_table(&body_json);
                table
                    .array_orientation(json_to_table::Orientation::Row)
                    .object_orientation(json_to_table::Orientation::Row)
                    .collapse();
                println!("{}", table.to_string());
            } else {
                println!("❌ Request to Pipeless node was not successful. Status code: {}", status);
                println!("👉 Error message: {}", body);
            }
        },
        Err(err) => {
            println!("❌ Failed to send request to Pipeless node.");
            println!("👉 Error message: {}", err.to_string());
        }
    }
}
