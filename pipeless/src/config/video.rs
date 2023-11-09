#[derive(Clone)]
pub struct Video {
    /// This can be input or output video, it is generic
    protocol: String,
    location: String,
    uri: String,
}
impl Video {
    pub fn new(uri: String) -> Self {
        let mut protocol: String;
        let mut location: String;
        if uri == "screen" {
            // Output to the screen
            protocol = String::from("screen");
            location = String::from("screen");
        } else if uri != "v4l2" {
            let uri_split: Vec<&str> = uri.split("://").collect();
            protocol = uri_split.get(0).expect("Unable to get protocol from URI").to_string();
            location = uri_split.get(1).expect("Unable to get location from URI. Ensure it contains the protocol followed by '//'.").to_string();
            if protocol == "file" && !location.starts_with('/') {
                panic!("When using files you should indicate an absolute path. Ensure your path is on the format file:///some/path (note there are 3 slashes)");
            }
        } else {
            protocol = String::from("v4l2");
            location = String::from("v4l2");
        }

        Video { protocol, location, uri, }
    }

    pub fn get_protocol(&self) -> &str {
        &self.protocol
    }
    pub fn get_location(&self) -> &str {
        &self.location
    }
    pub fn get_uri(&self) -> &str {
        &self.uri
    }
}
