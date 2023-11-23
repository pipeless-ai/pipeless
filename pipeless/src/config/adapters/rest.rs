use std::{sync::Arc, convert::Infallible};
use tokio::sync::RwLock;
use log::info;
use serde_json::json;
use warp::Filter;
use serde_derive::{Deserialize, Serialize};

use crate::{self as pipeless};

#[derive(Clone, Deserialize, Serialize)]
struct StreamBody {
    // Both are optional because we re-use this over requests
    input_uri: Option<String>,
    output_uri: Option<String>,
    frame_path: Option<Vec<String>>,
}

async fn handle_get_streams(
    streams_table: Arc<RwLock<pipeless::config::streams::StreamsTable>>,
) -> Result<warp::reply::WithStatus<warp::reply::Json>, Infallible> {
    let table = streams_table.read()
        .await
        .get_table();

    Ok(warp::reply::with_status(
        warp::reply::json(&json!(table)),
        warp::http::StatusCode::OK,
    ))
}

async fn handle_add_stream(
    stream: StreamBody,
    streams_table: Arc<RwLock<pipeless::config::streams::StreamsTable>>,
    dispatcher_sender: tokio::sync::mpsc::UnboundedSender<pipeless::dispatcher::DispatcherEvent>
) -> Result<warp::reply::WithStatus<warp::reply::Json>, Infallible> {
    let input_uri: String;
    if let Some(uri) = stream.clone().input_uri {
        input_uri = uri;
    } else {
        return Ok(warp::reply::with_status(
            warp::reply::json(&json!({"error": "Missing input URI"})),
            warp::http::StatusCode::BAD_REQUEST,
        ));
    }
    let frame_path;
    if let Some(path) = stream.clone().frame_path {
        frame_path = path;
    } else {
        return Ok(warp::reply::with_status(
            warp::reply::json(&json!({"error": "Missing frame path. The ordered array of stages that the frame will go through"})),
            warp::http::StatusCode::BAD_REQUEST,
        ));
    }
    let output_uri = stream.output_uri.clone();
    {
        let res = streams_table.write()
            .await
            .add(pipeless::config::streams::StreamsTableEntry::new(input_uri, output_uri, frame_path));

        if let Err(err) = res {
            return Ok(warp::reply::with_status(
                warp::reply::json(&json!({"error": format!("Error adding new stream to the table: {}", err)})),
                warp::http::StatusCode::INTERNAL_SERVER_ERROR,
            ));
        }
    }

    match dispatcher_sender.send(pipeless::dispatcher::DispatcherEvent::TableChange) {
        Err(err) => {
            return Ok(warp::reply::with_status(
                warp::reply::json(&json!({"error": err.to_string()})),
                warp::http::StatusCode::INTERNAL_SERVER_ERROR,
            ));
        }
        Ok(_o) => (),
    }

    Ok(warp::reply::with_status(
        warp::reply::json(&stream),
        warp::http::StatusCode::OK,
    ))
}

async fn handle_update_stream(
    id: uuid::Uuid,
    stream: StreamBody,
    streams_table: Arc<RwLock<pipeless::config::streams::StreamsTable>>,
    dispatcher_sender: tokio::sync::mpsc::UnboundedSender<pipeless::dispatcher::DispatcherEvent>
) -> Result<warp::reply::WithStatus<warp::reply::Json>, Infallible> {
    let input_uri: String;
    if let Some(uri) = stream.clone().input_uri {
        input_uri = uri;
    } else {
        if let Some(entry) = streams_table.read()
            .await
            .get_entry_by_id(id)
        {
            input_uri = entry.get_input_uri().to_string();
        } else {
            return Ok(warp::reply::with_status(
                warp::reply::json(&json!({"error": "Stream entry not found"})),
                warp::http::StatusCode::NOT_FOUND,
            ));
        }
    }
    let mut frame_path: Vec<String> = vec![];
    if let Some(path) = stream.clone().frame_path {
        frame_path = path;
    }
    if frame_path.len() == 0 {
        if let Some(entry) = streams_table.read()
            .await
            .get_entry_by_id(id)
        {
            frame_path = entry.get_frame_path().to_owned();
        } else {
            return Ok(warp::reply::with_status(
                warp::reply::json(&json!({"error": "Frame path not found in stream"})),
                warp::http::StatusCode::NOT_FOUND,
            ));
        }
    }
    let mut output_uri: Option<String> = stream.clone().output_uri;
    if output_uri.is_none() {
        if let Some(entry) = streams_table.read()
            .await
            .get_entry_by_id(id)
        {
            output_uri = entry.get_output_uri().map(|s| s.to_string());
        } else {
            return Ok(warp::reply::with_status(
                warp::reply::json(&json!({"error": "Stream entry not found"})),
                warp::http::StatusCode::NOT_FOUND,
            ));
        }
    }
    {
        streams_table.write()
            .await
            .update_by_entry_id(id, &input_uri, output_uri, frame_path);
    }

    match dispatcher_sender.send(pipeless::dispatcher::DispatcherEvent::TableChange) {
        Err(err) => {
            return Ok(warp::reply::with_status(
                warp::reply::json(&json!({"error": err.to_string()})),
                warp::http::StatusCode::INTERNAL_SERVER_ERROR,
            ));
        }
        Ok(_o) => (),
    }

    Ok(warp::reply::with_status(
        warp::reply::json(&stream),
        warp::http::StatusCode::OK,
    ))
}

async fn handle_remove_stream(
    id: uuid::Uuid,
    streams_table: Arc<RwLock<pipeless::config::streams::StreamsTable>>,
    dispatcher_sender: tokio::sync::mpsc::UnboundedSender<pipeless::dispatcher::DispatcherEvent>
) -> Result<warp::reply::WithStatus<warp::reply::Json>, Infallible> {
    let option_entry = streams_table.write()
        .await
        .remove(id);

    if let Some(entry) = option_entry {
        let stream = StreamBody {
            input_uri: Some(entry.get_input_uri().to_string()),
            output_uri: entry.get_output_uri().map(|s| s.to_string()),
            frame_path: Some(entry.get_frame_path().to_owned()),
        };

        match dispatcher_sender.send(pipeless::dispatcher::DispatcherEvent::TableChange) {
            Err(err) => {
                return Ok(warp::reply::with_status(
                    warp::reply::json(&json!({"error": err.to_string()})),
                    warp::http::StatusCode::INTERNAL_SERVER_ERROR,
                ));
            }
            Ok(_o) => (),
        }

        Ok(warp::reply::with_status(
            warp::reply::json(&stream),
            warp::http::StatusCode::OK,
        ))
    } else {
        Ok(warp::reply::with_status(
            warp::reply::json(&json!({"error": "Stream entry not found"})),
            warp::http::StatusCode::NOT_FOUND,
        ))
    }

}

/// The REST config adapter allows to edit the streams config table via a REST API
/// Ex:
///    $ curl -X POST localhost:1234/new_stream?input="some_uri"&output="some_uri"
///
pub struct RestAdapter {
    streams_table: Arc<RwLock<pipeless::config::streams::StreamsTable>>,
}
impl RestAdapter {
    pub fn new(streams_table: Arc<RwLock<pipeless::config::streams::StreamsTable>>) -> Self {
        Self { streams_table }
    }

    pub fn start(
        &self,
        _dispatcher_sender: tokio::sync::mpsc::UnboundedSender<pipeless::dispatcher::DispatcherEvent>
    ) {
        let streams_table = self.streams_table.clone();
        let dispatcher_sender = _dispatcher_sender.clone();

        let get_streams = warp::get()
            .and(warp::path("streams"))
            .then({
                let streams_table = streams_table.clone();
                move || {
                    let streams_table = streams_table.clone();
                    async move {
                        handle_get_streams(streams_table).await
                    }
                }
            });

        let add_stream = warp::post()
            .and(warp::path("streams"))
            .and(warp::body::json())
            .then({
                let streams_table = streams_table.clone();
                let dispatcher_sender = dispatcher_sender.clone();
                move |stream| {
                    let streams_table = streams_table.clone();
                    let dispatcher_sender = dispatcher_sender.clone();
                    async move {
                        handle_add_stream(stream, streams_table, dispatcher_sender).await
                    }
                }
            });

        let update_stream = warp::put()
            .and(warp::path("streams"))
            .and(warp::path::param::<uuid::Uuid>())
            .and(warp::body::json())
            .then({
                let streams_table = streams_table.clone();
                let dispatcher_sender = dispatcher_sender.clone();
                move |id: uuid::Uuid, stream: StreamBody| {
                    let streams_table = streams_table.clone();
                    let dispatcher_sender = dispatcher_sender.clone();
                    async move {
                        handle_update_stream(id, stream, streams_table, dispatcher_sender).await
                    }
                }
            });

        let remove_stream = warp::delete()
            .and(warp::path("streams"))
            .and(warp::path::param::<uuid::Uuid>())
            .then({
                let streams_table = streams_table.clone();
                let dispatcher_sender = dispatcher_sender.clone();
                move |id: uuid::Uuid| {
                    let streams_table = streams_table.clone();
                    let dispatcher_sender = dispatcher_sender.clone();
                    async move {
                        handle_remove_stream(id, streams_table, dispatcher_sender).await
                    }
                }
            });

        let streams_endpoint = get_streams
            .or(add_stream)
            .or(update_stream)
            .or(remove_stream);

        let server = warp::serve(streams_endpoint)
            .run(([127, 0, 0, 1], 3030));

        info!("REST adapter running");

        // Run server as a tokio task
        tokio::spawn(server);
    }
}