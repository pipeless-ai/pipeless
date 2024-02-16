use log::{info, error};

use crate as pipeless;
use pipeless::stages::stage::FromComponentContextTrait;

// This bingen creates pipeless::stages::languages::wasm::exports::pipeless_wasm
// which contains the WIT interfaces
// For example super::wasm::exports::pipeless_wasm::hooks::hook_interface::HookInterface
wasmtime::component::bindgen!({
    path: "src/components/builder/wit",
    world: "hook-component"
});

pub struct ServerWasiView {
    table: wasmtime_wasi::preview2::ResourceTable,
    ctx: wasmtime_wasi::preview2::WasiCtx,
}

impl ServerWasiView {
    pub fn new() -> Self {
        let table = wasmtime_wasi::preview2::ResourceTable::new();
        let ctx = wasmtime_wasi::preview2::WasiCtxBuilder::new().inherit_stdio().build();

        Self { table, ctx }
    }
}

impl wasmtime_wasi::preview2::WasiView for ServerWasiView {
    fn table(&self) -> &wasmtime_wasi::preview2::ResourceTable {
        &self.table
    }

    fn table_mut(&mut self) -> &mut wasmtime_wasi::preview2::ResourceTable {
        &mut self.table
    }

    fn ctx(&self) -> &wasmtime_wasi::preview2::WasiCtx {
        &self.ctx
    }

    fn ctx_mut(&mut self) -> &mut wasmtime_wasi::preview2::WasiCtx {
        &mut self.ctx
    }
}

// TODO: we have to pass the context to the hook call, we are not passing it right now for the test
pub struct WasmStageContext {
    // TODO: add here the context wasm store
    // TODO: what type should we add here? For Python we use dicts, but in this case we ned a more general one. Maybe the same as the user_data in the frame?
    context: u32,
}
impl WasmStageContext {
    pub fn new(context: u32) -> Self {
        Self {
            context
        }
    }
}
impl FromComponentContextTrait<WasmStageContext> for WasmStageContext {
    fn init_context(stage_name: &str, component: &wasmtime::component::Component) -> Self {
        info!("Initializing context for stage: {}", stage_name);
        let mut store = wasmtime::Store::new(&pipeless::components::engine::WASM_ENGINE.get_engine(), {});
        let linker = wasmtime::component::Linker::new(&pipeless::components::engine::WASM_ENGINE.get_engine());
        let (_, component_instance) = HookComponent::instantiate(&mut store, &component, &linker).unwrap();
        if let Some(init_func) = component_instance.get_func(&mut store, "init") {
            let typed_init_func = init_func.typed::<(), (u32,)>(&store).unwrap();
            let stage_ctx = typed_init_func.call(store, ()).unwrap();
            WasmStageContext { context: stage_ctx.0 } // FIXME: replace u32 by whatever type we will use
        } else {
            error!("Unable to create context from wasm hook. init function not found");
            WasmStageContext { context: 0 } // FIXME: initialize empty context once we replace u32 by whatever type is correct
        }
    }
}


// Export modules for wasm hooks
pub mod wasm_stateful;
pub mod wasm_stateless;
