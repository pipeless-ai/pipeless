
#[derive(Debug)]
pub struct VideoConfigError {
    msg: String
}
impl VideoConfigError {
    fn new(msg: &str) -> Self {
        Self { msg: msg.to_owned() }
    }
}
impl std::error::Error for VideoConfigError {}
impl std::fmt::Display for VideoConfigError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.msg.to_string())
    }
}

#[derive(Clone)]
pub struct Video {
    /// This can be input or output video, it is generic
    protocol: String,
    location: String,
    uri: String,
}
impl Video {
    pub fn new(uri: String) -> Result<Self, VideoConfigError> {
        let protocol: String;
        let location: String;
        if uri == "screen" {
            // Output to the screen
            protocol = String::from("screen");
            location = String::from("screen");
        } else if !uri.starts_with("v4l2") {
            let uri_split: Vec<&str> = uri.split("://").collect();
            protocol = uri_split.get(0).ok_or_else(|| { VideoConfigError::new("Unable to get protocol from URI") })?.to_string();
            location = uri_split.get(1)
                .ok_or_else(|| { VideoConfigError::new("Unable to get location from URI. Ensure it contains the protocol followed by '://'. Example: file:///home/user/file.mp4") })?.to_string();
            if protocol == "file" && !location.starts_with('/') {
                panic!("When using files you should indicate an absolute path. Ensure your path is on the format file:///home/user/file.mp4 (note there are 3 slashes)");
            }
        } else {
            protocol = String::from("v4l2");
            location = String::from("v4l2");
        }

        Ok(Video { protocol, location, uri, })
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
