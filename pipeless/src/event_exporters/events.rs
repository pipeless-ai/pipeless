use std::fmt;
use log::warn;

pub enum EventType {
    StreamStartError,
    StreamFinished,
}
impl fmt::Display for EventType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            EventType::StreamStartError => write!(f, "StreamStartError"),
            EventType::StreamFinished => write!(f, "StreamFinished"),
        }
    }
}

/*
 * Exports a stream finished event to the external event exporter when it is enabled
 */
pub async fn export_stream_finished_event(stream_uuid: uuid::Uuid, stream_end_state: &str) {
    let ext_event: serde_json::Value = serde_json::json!({
        "type": EventType::StreamFinished.to_string(),
        "end_state": stream_end_state,
        "stream_uuid": stream_uuid.to_string(),
    });
    let ext_event_json_str = serde_json::to_string(&ext_event);
    if let Ok(json_str) = ext_event_json_str {
        super::EVENT_EXPORTER.lock().await.publish(&json_str).await;
    } else {
        warn!("Error serializing event to JSON string, skipping external publishing");
    }
}

/*
 * Exports a stream start error event to the external event exporter when it is enabled
 */
pub async fn export_stream_start_error_event(stream_uuid: uuid::Uuid) {
    let ext_event: serde_json::Value = serde_json::json!({
        "type": EventType::StreamStartError.to_string(),
        "end_state": "error",
        "stream_uuid": stream_uuid.to_string(),
    });
    let ext_event_json_str = serde_json::to_string(&ext_event);
    if let Ok(json_str) = ext_event_json_str {
        super::EVENT_EXPORTER.lock().await.publish(&json_str).await;
    } else {
        warn!("Error serializing event to JSON string, skipping external publishing");
    }
}
