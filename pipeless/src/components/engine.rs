use lazy_static::lazy_static;

pub struct WasmEngine {
    engine: wasmtime::Engine,
}
impl WasmEngine {
    fn new() -> Self {
        let mut config = wasmtime::Config::new();
        config.wasm_component_model(true);
        config.debug_info(true);

        let engine = wasmtime::Engine::new(&config).unwrap();
        Self { engine }
    }

    pub fn get_engine(&self) -> &wasmtime::Engine {
        &self.engine
    }
}

lazy_static! {
    pub static ref WASM_ENGINE: WasmEngine = WasmEngine::new();
}
