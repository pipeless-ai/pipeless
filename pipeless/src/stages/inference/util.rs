use reqwest::blocking::get;
use std::fs::File;
use std::io::Write;

/// Get a model local ile path from a URI
pub fn get_model_path(uri: &str, alias: &str) -> Result<String, String> {
    // TODO: support download from private s3 buckets
    if uri.starts_with("file://") {
        let model_file_path = uri.replace("file://", "");
        Ok(model_file_path.to_string())
    } else if uri.starts_with("http") {
        let response = get(uri).unwrap();
        if response.status().is_success() {
            let model_file_path = format!("/tmp/{}-model.onnx", alias);
            let mut model_file = File::create(&model_file_path).unwrap();
            model_file.write_all(&response.bytes().unwrap()).unwrap();
            Ok(model_file_path)
        } else {
            Err(format!("HTTP request failed with status code: {}", response.status()).into())
        }
    } else {
        Err("The model URI currently supports 'file://' and 'http(s)://'".into())
    }
}