use std::sync::Arc;

use log::warn;
use redis::AsyncCommands;
use lazy_static::lazy_static;
use tokio::sync::Mutex;

pub mod events;

pub enum EventExporterEnum {
    Redis(Redis),
}

/*
 * General event exporter that wraps many types of event exporters
 * We cannot use the typical Box<dyn ExporterTrait> to create a common interface because trait methods cannot be async so we just create variants and invoke theit methods
 */
pub struct EventExporter {
    exporter: Option<EventExporterEnum>,
}
impl EventExporter {
    pub fn new_none_exporter() -> Self {
        Self { exporter: None }
    }
    pub async fn new_redis_exporter(redis_url: &str, channel: &str) -> Self {
        Self {
            exporter: Some(EventExporterEnum::Redis(Redis::new(redis_url, channel).await)),
        }
    }
    pub async fn publish(&mut self, message: &str) {
        if let Some(exporter) = &mut self.exporter {
            match exporter {
                EventExporterEnum::Redis(pblsr) => pblsr.publish(message).await,
            }
        }
    }
}

/*
 * Redis event exporter
 */
pub struct Redis {
    connection: redis::aio::Connection,
    channel: String,
}
impl Redis {
    async fn new(redis_url: &str, channel: &str) -> Self {
        let client = redis::Client::open(redis_url).expect("Unable to create Redis client with the provided URL, please check the value of the PIPELESS_REDIS_URL env var");
        let con = client.get_tokio_connection().await.expect("Failed to connect to Redis");

        Self { connection: con, channel: channel.to_owned() }
    }

    async fn publish(&mut self, message: &str) {
        if let Err(err) = self.connection.publish::<&str, &str, i32>(&self.channel, message).await  {
            warn!("Error publishing message to Redis: {}", err.to_string());
        }
    }
}

// Create global variable to access the event exporter from any point of the code
// It uses an Arc to be shared among threads and a Mutex since the connection is updated on every push
lazy_static! {
    pub static ref EVENT_EXPORTER: Arc<Mutex<EventExporter>> =
        Arc::new(Mutex::new(EventExporter::new_none_exporter()));
}
