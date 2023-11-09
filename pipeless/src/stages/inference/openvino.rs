use crate as pipeless;

use super::session::SessionParams;

pub struct OpenvinoSessionParams {
}

pub struct OpenvinoSession {}
impl OpenvinoSession {
    pub fn new(model_uri: &str, params: SessionParams) -> Self {
        unimplemented!();
    }

    pub fn infer(frame: pipeless::data::Frame) {
        unimplemented!();
    }
}