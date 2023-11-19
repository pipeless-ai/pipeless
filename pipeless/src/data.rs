use std::{self, str::FromStr};
use ndarray;
use uuid;
use gstreamer as gst;

pub struct RgbFrame {
    uuid: uuid::Uuid,
    original: ndarray::Array3<u8>,
    modified: ndarray::Array3<u8>,
    width: usize,
    height: usize,
    pts: gst::ClockTime,
    dts: gst::ClockTime,
    duration: gst::ClockTime,
    fps: u8,
    input_ts: f64, // epoch in seconds
    inference_input: ndarray::ArrayBase<ndarray::OwnedRepr<f32>, ndarray::Dim<ndarray::IxDynImpl>>,
    inference_output: ndarray::ArrayBase<ndarray::OwnedRepr<f32>, ndarray::Dim<ndarray::IxDynImpl>>,
    pipeline_id: uuid::Uuid,
}
impl RgbFrame {
    pub fn new(
        original: ndarray::Array3<u8>,
        width: usize, height: usize,
        pts: gst::ClockTime, dts: gst::ClockTime, duration: gst::ClockTime,
        fps: u8, input_ts: f64,
        pipeline_id: uuid::Uuid,
    ) -> Self {
        let modified = original.to_owned();
        RgbFrame {
            uuid: uuid::Uuid::new_v4(),
            original, modified,
            width, height,
            pts, dts, duration, fps,
            input_ts,
            inference_input: ndarray::ArrayBase::zeros(ndarray::IxDyn(&[0])),
            inference_output: ndarray::ArrayBase::zeros(ndarray::IxDyn(&[0])),
            pipeline_id,
        }
    }

    pub fn from_values(
        uuid: &str,
        original: ndarray::Array3<u8>,
        modified: ndarray::Array3<u8>,
        width: usize, height: usize,
        pts: u64, dts: u64, duration: u64,
        fps: u8, input_ts: f64,
        inference_input: ndarray::ArrayBase<ndarray::OwnedRepr<f32>, ndarray::Dim<ndarray::IxDynImpl>>,
        inference_output: ndarray::ArrayBase<ndarray::OwnedRepr<f32>, ndarray::Dim<ndarray::IxDynImpl>>,
        pipeline_id: &str,
    ) -> Self {
        RgbFrame {
            uuid: uuid::Uuid::from_str(uuid).unwrap(),
            original, modified,
            width, height,
            pts: gst::ClockTime::from_mseconds(pts),
            dts: gst::ClockTime::from_mseconds(dts),
            duration: gst::ClockTime::from_mseconds(duration),
            fps, input_ts,
            inference_input, inference_output,
            pipeline_id: uuid::Uuid::from_str(pipeline_id).unwrap(),
        }
    }

    pub fn set_original_pixels(&mut self, original_pixels: ndarray::Array3<u8>) {
        self.original = original_pixels
    }
    pub fn get_original_pixels(&self) -> &ndarray::Array3<u8> {
        &self.original
    }
    pub fn get_owned_original_pixels(&self) -> ndarray::Array3<u8> {
        self.original.to_owned()
    }
    pub fn get_modified_pixels(&self) -> &ndarray::Array3<u8> {
        &self.modified
    }
    pub fn get_owned_modified_pixels(&self) -> ndarray::Array3<u8> {
        self.modified.to_owned()
    }
    pub fn get_mutable_pixels(&mut self) -> ndarray::ArrayViewMut3<u8> {
        self.modified.view_mut()
    }
    pub fn update_mutable_pixels(
        &mut self, view_mut: ndarray::ArrayViewMut3<u8>
    ) {
        self.modified.assign(&view_mut);
    }
    pub fn get_uuid(&self) -> uuid::Uuid {
        self.uuid
    }
    pub fn get_fps(&self) -> u8 {
        self.fps
    }
    pub fn get_pts(&self) -> gst::ClockTime {
        self.pts
    }
    pub fn get_dts(&self) -> gst::ClockTime {
        self.dts
    }
    pub fn get_width(&self) -> usize {
        self.width
    }
    pub fn get_height(&self) -> usize {
        self.height
    }
    pub fn get_duration(&self) -> gst::ClockTime {
        self.duration
    }
    pub fn get_input_ts(&self) -> f64 {
        self.input_ts
    }
    pub fn get_inference_input(&self) -> &ndarray::ArrayBase<ndarray::OwnedRepr<f32>, ndarray::Dim<ndarray::IxDynImpl>> {
        &self.inference_input
    }
    pub fn get_inference_output(&self) -> &ndarray::ArrayBase<ndarray::OwnedRepr<f32>, ndarray::Dim<ndarray::IxDynImpl>> {
        &self.inference_output
    }
    pub fn set_inference_input(&mut self, input_data: ndarray::ArrayBase<ndarray::OwnedRepr<f32>, ndarray::Dim<ndarray::IxDynImpl>>) {
        self.inference_input = input_data;
    }
    pub fn set_inference_output(&mut self, output_data: ndarray::ArrayBase<ndarray::OwnedRepr<f32>, ndarray::Dim<ndarray::IxDynImpl>>) {
        self.inference_output = output_data;
    }
    pub fn get_pipeline_id(&self) -> uuid::Uuid {
        self.pipeline_id
    }
    pub fn set_pipeline_id(&mut self, pipeline_id: &str) {
        self.pipeline_id = uuid::Uuid::from_str(pipeline_id).unwrap();
    }
}

pub enum Frame {
    RgbFrame(RgbFrame)
}
impl Frame {
    pub fn new_rgb(
        original: ndarray::Array3<u8>,
        width: usize, height: usize,
        pts: gst::ClockTime, dts: gst::ClockTime, duration: gst::ClockTime,
        fps: u8, input_ts: f64,
        pipeline_id: uuid::Uuid
    ) -> Self {
        let rgb = RgbFrame::new(
            original, width, height,
            pts, dts, duration,
            fps, input_ts, pipeline_id
        );
        Self::RgbFrame(rgb)
    }

    pub fn set_original_pixels(&mut self, original_pixels: ndarray::Array3<u8>) {
        match self {
            Frame::RgbFrame(frame) => { frame.set_original_pixels(original_pixels) },
        }
    }
    pub fn get_original_pixels(&self) -> &ndarray::Array3<u8> {
        match self {
            Frame::RgbFrame(frame) => frame.get_original_pixels()
        }
    }
    pub fn get_inference_input(&self) -> &ndarray::ArrayBase<ndarray::OwnedRepr<f32>, ndarray::Dim<ndarray::IxDynImpl>> {
        match self {
            Frame::RgbFrame(frame) => frame.get_inference_input()
        }
    }
    pub fn get_inference_output(&self) -> &ndarray::ArrayBase<ndarray::OwnedRepr<f32>, ndarray::Dim<ndarray::IxDynImpl>> {
        match self {
            Frame::RgbFrame(frame) => frame.get_inference_output()
        }
    }
    pub fn set_inference_input(&mut self, input_data: ndarray::ArrayBase<ndarray::OwnedRepr<f32>, ndarray::Dim<ndarray::IxDynImpl>>) {
        match self {
            Frame::RgbFrame(frame) => { frame.set_inference_input(input_data); },
        }
    }
    pub fn set_inference_output(&mut self, output_data: ndarray::ArrayBase<ndarray::OwnedRepr<f32>, ndarray::Dim<ndarray::IxDynImpl>>) {
        match self {
            Frame::RgbFrame(frame) => { frame.set_inference_output(output_data); },
        }
    }
}