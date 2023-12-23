use crate as pipeless;

use super::session::SessionParams;

pub struct OpenvinoSessionParams {
}

pub struct OpenvinoSession {}
impl OpenvinoSession {
    pub fn new(_model_uri: &str, _params: SessionParams) -> Self {
        unimplemented!();
    }


}
impl super::session::SessionTrait for OpenvinoSession {
    fn infer(&self, _frame: pipeless::frame::Frame) -> pipeless::frame::Frame {
        unimplemented!();
    }
}
