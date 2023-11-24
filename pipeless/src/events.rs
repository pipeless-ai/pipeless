use futures::{StreamExt, Future};
use gst::TagList;
use log::{error, info, warn};
use gstreamer as gst;

use crate as pipeless;

trait EventType {}

pub struct FrameChange {
    // Events own the frame allowing them to freely flow inside pipeless
    frame: pipeless::data::Frame,
}
impl FrameChange {
    pub fn new(frame: pipeless::data::Frame) -> Self {
        Self { frame }
    }
    pub fn get_frame(&self) -> &pipeless::data::Frame {
        &self.frame
    }
    pub fn into_frame(self) -> pipeless::data::Frame {
        self.frame
    }
}
impl EventType for FrameChange {}

pub struct TagsChange {
    tags: gst::TagList,
}
impl TagsChange {
    pub fn new(tags: gst::TagList) -> Self {
        Self { tags }
    }
    pub fn get_tags(&self) -> &TagList {
        &self.tags
    }
}
impl EventType for TagsChange {}

// When the input stream stopped sending frames
pub struct EndOfInputStream {}
impl EndOfInputStream {
    pub fn new() -> Self {
        Self {}
    }
}
impl EventType for EndOfInputStream {}

// When the output stream processed the input EOS
pub struct EndOfOutputStream {}
impl EndOfOutputStream {
    pub fn new() -> Self {
        Self {}
    }
}
impl EventType for EndOfOutputStream {}

// When the input stream caps are available
pub struct NewInputCaps {
    caps: String,
}
impl NewInputCaps {
    pub fn new(caps: String) -> Self {
        Self { caps }
    }
    pub fn get_caps(&self) -> &str {
        &self.caps
    }
}
impl EventType for NewInputCaps {}

pub struct InputStreamError {
    msg: String,
}
impl InputStreamError {
    pub fn new(err: &str) -> Self {
        Self { msg: err.to_string() }
    }
    pub fn get_msg(&self) -> &str {
        &self.msg
    }
}
impl EventType for InputStreamError {}

pub struct OutputStreamError {
    msg: String,
}
impl OutputStreamError {
    pub fn new(err: &str) -> Self {
        Self { msg: err.to_string() }
    }
    pub fn get_msg(&self) -> &str {
        &self.msg
    }
}
impl EventType for OutputStreamError {}

pub enum Event {
    FrameChangeEvent(FrameChange),
    TagsChangeEvent(TagsChange),
    EndOfInputStreamEvent(EndOfInputStream),
    EndOfOutputStreamEvent(EndOfOutputStream),
    NewInputCapsEvent(NewInputCaps),
    InputStreamErrorEvent(InputStreamError),
    OutputStreamErrorEvent(OutputStreamError),
}
impl Event {
    pub fn new_frame_change(frame: pipeless::data::Frame) -> Self {
        let frame_change = FrameChange::new(frame);
        Self::FrameChangeEvent(frame_change)
    }
    pub fn new_tags_change(tags: gst::TagList) -> Self {
        let tags_change = TagsChange::new(tags);
        Self::TagsChangeEvent(tags_change)
    }
    pub fn new_end_of_input_stream() -> Self {
        let eos_input = EndOfInputStream::new();
        Self::EndOfInputStreamEvent(eos_input)
    }
    pub fn new_end_of_output_stream() -> Self {
        let eos_output = EndOfOutputStream::new();
        Self::EndOfOutputStreamEvent(eos_output)
    }
    pub fn new_input_caps(caps: String) -> Self {
        let new_input_caps = NewInputCaps::new(caps);
        Self::NewInputCapsEvent(new_input_caps)
    }
    pub fn new_input_stream_error(err: &str) -> Self {
        let input_error = InputStreamError::new(err);
        Self::InputStreamErrorEvent(input_error)
    }
    pub fn new_output_stream_error(err: &str) -> Self {
        let output_error = OutputStreamError::new(err);
        Self::OutputStreamErrorEvent(output_error)
    }
}

/// The bus is used to handle events on the pipelines.
/// working as expected even on different threads
// TODO: we should implement two kind of buses,
//       a cloud bus and a local bus. The cloud bus will basically
//       be a connection to a message broker.
pub struct Bus {
    sender: tokio::sync::mpsc::UnboundedSender<Event>,
    // Use a stream receiver to be able to process events concurrently
    receiver: tokio_stream::wrappers::UnboundedReceiverStream<Event>,
}
impl Bus {
    pub fn new() -> Self {
        let (sender, receiver) = tokio::sync::mpsc::unbounded_channel::<Event>();
        Self {
            sender,
            receiver: tokio_stream::wrappers::UnboundedReceiverStream::new(
                receiver
            ),
        }
    }

    pub fn get_sender(&self) -> tokio::sync::mpsc::UnboundedSender<Event> {
        self.sender.clone()
    }

    pub async fn process_events<F, Fut>(self, limit: usize, mut func: F)
    where
        F: FnMut(Event, tokio::sync::mpsc::Sender<()>) -> Fut,
        Fut: Future<Output = ()>,
    {
        // This channel is only used as condition to exit the for_each_concurrent
        // The callback passed to process_events simply has to invoke: end_signal.send(())
        let (tx, mut rx) = tokio::sync::mpsc::channel::<()>(1);

        tokio::select! {
            _ = self.receiver.for_each_concurrent(limit, |event| func(event, tx.clone())) => error!("This should not be reached!"),
            _ = rx.recv() => info!("Stream loop stopped"),
        };
    }
}

/*
Utils to produce sync events. Can be called anywhere within sync code.
We use them to publish events from Gstreamer pipeline callback.

NOTE: We can use the send method in both, sync and async contexts, only
because the tokio unbounded channel never requires any form of waiting.
Before moving to Tokio channels, we were using the async_channels crate,
and we had to create different methods for sync and async code since
we cannot await in the Gstreamer callbacks
*/
pub fn publish_new_frame_change_event_sync(
    bus_sender: &tokio::sync::mpsc::UnboundedSender<Event>,
    frame: pipeless::data::Frame
) {
    let new_frame_event = Event::new_frame_change(frame);
    if let Err(err) = bus_sender.send(new_frame_event) {
        warn!("Error sending frame change event: {}", err);
    }
    error!("Event sent!");
}

pub fn publish_input_eos_event_sync(
    bus_sender: &tokio::sync::mpsc::UnboundedSender<Event>,
) {
    let eos_event = Event::new_end_of_input_stream();
    if let Err(err) = bus_sender.send(eos_event) {
        warn!("Error sending input EOS event: {}", err);
    }
}

pub fn publish_ouptut_eos_event_sync(
    bus_sender: &tokio::sync::mpsc::UnboundedSender<Event>,
) {
    let eos_event = Event::new_end_of_output_stream();
    if let Err(err) = bus_sender.send(eos_event) {
        warn!("Error sending output EOS event: {}", err);
    }
}

pub fn publish_input_tags_changed_event_sync(
    bus_sender: &tokio::sync::mpsc::UnboundedSender<Event>,
    tags: gst::TagList
) {
    let tags_change_event = Event::new_tags_change(tags);
    if let Err(err) = bus_sender.send(tags_change_event) {
        warn!("Error sending tags change event: {}", err);
    }
}

pub fn publish_new_input_caps_event_sync(
    bus_sender: &tokio::sync::mpsc::UnboundedSender<Event>,
    caps: String
) {
    let new_input_caps_event = Event::new_input_caps(caps);
    if let Err(err) = bus_sender.send(new_input_caps_event) {
        warn!("Error sending new input caps event: {}", err);
    }
}

pub fn publish_input_stream_error_event_sync(
    bus_sender: &tokio::sync::mpsc::UnboundedSender<Event>,
    err: &str
) {
    let input_stream_error_event = Event::new_input_stream_error(err);
    if let Err(err) = bus_sender.send(input_stream_error_event) {
        warn!("Error sending input stream error event: {}", err);
    }
}

pub fn publish_output_stream_error_event_sync(
    bus_sender: &tokio::sync::mpsc::UnboundedSender<Event>,
    err: &str
) {
    let output_stream_error_event = Event::new_output_stream_error(err);
    if let Err(err) = bus_sender.send(output_stream_error_event) {
        warn!("Error sending output stream error event: {}", err);
    }
}