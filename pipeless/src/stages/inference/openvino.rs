use crate as pipeless;

use super::session::SessionParams;

pub struct OpenvinoSessionParams {
}

pub struct OpenvinoSession {}
impl OpenvinoSession {
    pub fn new(_model_uri: &str, _params: SessionParams) -> Self {
        unimplemented!();
    }

    pub fn infer(_frame: pipeless::data::Frame) {
        unimplemented!();
    }
}