use env_logger;

pub fn setup_logger() {
    let mut log_builder = env_logger::Builder::new();
    let mut env = env_logger::Env::new();
    env = env.filter("PIPELESS_LOG_LEVEL").default_filter_or("INFO");
    log_builder.parse_env(env);
    log_builder.init();
}

//mod python;
pub mod pipeline;
pub mod input;
pub mod output;
pub mod config;
pub mod gst;
pub mod events;
pub mod frame;
pub mod dispatcher;
pub mod stages;
pub mod cli;
pub mod kvs;
