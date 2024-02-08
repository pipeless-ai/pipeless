use std::sync::Arc;
use log::{error, info};
use wasmtime::{AsContext, AsContextMut};
use crate::stages::stage::FromComponentContextTrait;
use crate as pipeless;
use crate::{data::Frame, stages::hook::{HookTrait, HookType}};

//fn main() -> Result<(), Box<dyn Error>> {
//    let mut config = Config::new();
//    config.wasm_component_model(true);
//    config.debug_info(true);
//    let engine = Engine::new(&config)?;
//    let component = Component::from_file(&engine, "./process.wasm")?;
//    let mut linker = Linker::new(&engine);
//    command::add_to_linker(&mut linker)?;
//    let table = Table::new();
//    let wasi = WasiCtxBuilder::new().inherit_stdio().build();
//    let mut store = Store::new(&engine, Ctx { table, wasi });
//    let (hook, _) = Hook::instantiate(&mut store, &component, &linker)?;
//    let result = hook.call_hook(
//        &mut store,
//        &Frame {
//            uuid: String::new(),
//            original: Vec::new(),
//            modified: Vec::new(),
//            width: 0,
//            height: 0,
//            pts: 0,
//            dts: 0,
//            duration: 0,
//            fps: 0,
//            input_timestamp: 0.0,
//            inference_input: Vec::new(),
//            inference_output: Vec::new(),
//            pipeline_id: String::new(),
//        },
//        &Context {
//            to_change: String::new(),
//        },
//    )?;
//    println!("result is: {result:?}");
//    Ok(())
//}

///////////////
struct ServerWasiView {
    table: wasmtime_wasi::preview2::ResourceTable,
    ctx: wasmtime_wasi::preview2::WasiCtx,
}

impl ServerWasiView {
    fn new() -> Self {
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

//impl AsContextMut for ServerWasiView {
//    fn as_context_mut(&mut self) -> wasmtime::StoreContextMut<'_, Self::Data> {
//
//    }
//}
////////////////

wasmtime::component::bindgen!({
    path: "src/components/builder/wit",
    world: "hook-component"
});

// TODO: we have to pass the context to the hook call, we are not passing it right now for the test
pub struct WasmStageContext {
    // TODO: what type should we add here? For Python we use dicts, but in this case we ned a more general one. Maybe the same as the user_data in the frame?
    context: u32,
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

pub struct WasmHook {
    //store: Arc<std::sync::Mutex<wasmtime::Store<ServerWasiView>>>,
    store: wasmtime::Store<ServerWasiView>,
    hook: HookComponent, // This is the bingen generated hook. TODO: should we create stages as wasm components or individual hooks?
    component_instance: wasmtime::component::Instance,
    component: wasmtime::component::Component,
}
impl WasmHook {
    pub fn new(hook_type: HookType, stage_name: &str, component: &wasmtime::component::Component) -> Self {
        // FIXME: is there any way we can prefix the component with the stage name and hook type for traceability like we do in python?
        let mut linker = wasmtime::component::Linker::new(&pipeless::components::engine::WASM_ENGINE.get_engine());
        wasmtime_wasi::preview2::command::sync::add_to_linker(&mut linker).unwrap();
        let wasi_view = ServerWasiView::new();
        //let wasi = wasmtime_wasi::WasiCtxBuilder::new()
        //    .inherit_stdio() // provide access to standard I/O
        //    .inherit_env().unwrap()
        //    .build();
        let mut store = wasmtime::Store::new(&pipeless::components::engine::WASM_ENGINE.get_engine(), wasi_view);
        let (hook, component_instance) = HookComponent::instantiate(&mut store, &component, &linker).unwrap();

        Self {
            //store: Arc::new(std::sync::Mutex::new(store)),
            store,
            hook,
            component_instance: component_instance,
            component: component.to_owned(),
        }
    }
}
impl HookTrait for WasmHook {
    fn exec_hook(&self, mut frame: Frame, stage_context: &pipeless::stages::stage::Context) -> Option<Frame> {
        let mut linker = wasmtime::component::Linker::new(&pipeless::components::engine::WASM_ENGINE.get_engine());
        wasmtime_wasi::preview2::command::sync::add_to_linker(&mut linker).unwrap();
        let wasi_view = ServerWasiView::new();
        let mut store = wasmtime::Store::new(&pipeless::components::engine::WASM_ENGINE.get_engine(), wasi_view);
        let (hook, component_instance) = HookComponent::instantiate(&mut store, &self.component, &linker).unwrap();


        // FIXME: Use the stage context. We have to resolve the type to use since we cannot create dictionaries as it requires recursive types
        let stage_context = match stage_context {
            crate::stages::stage::Context::WasmContext(wasm_context) => wasm_context,
            crate::stages::stage::Context::EmptyContext => &WasmStageContext { context: 0 },
            _ =>  {
                error!("The stage context provided to the Wasm executor is not a Wasm context. Defaulting to empty context to avoid failure.");
                &WasmStageContext { context: 0 }
            }
        };

        if let pipeless::data::Frame::RgbFrame(mut frame) = frame {
            // FIXME: we must avoid this copy from the Rust struct to the Wit defined data type
            let wasm_rgb_frame = pipeless_wasm::hooks::types::WasmRgbFrame {
                uuid: frame.get_uuid().to_string(),
                original: convert_to_vec_3d(frame.get_original_pixels().to_owned()), // FIXME: we are copying the frame on the to_owned and later again on the function to convert to vec
                modified: convert_to_vec_3d(frame.get_modified_pixels().to_owned()), // FIXME: we are copying the frame on the to_owned and later again on the function to convert to vec
                width: frame.get_width() as u32,
                height: frame.get_height() as u32,
                pts: frame.get_pts().mseconds(),
                dts: frame.get_dts().mseconds(),
                duration: frame.get_duration().mseconds(),
                fps: frame.get_fps(),
                input_ts: frame.get_input_ts(),
                inference_input: convert_to_vec_3d(frame.get_inference_input().to_owned()), // FIXME: we are copying the frame on the to_owned and later again on the function to convert to vec
                inference_output: convert_to_vec_3d(frame.get_inference_output().to_owned()), // FIXME: we are copying the frame on the to_owned and later again on the function to convert to vec
                pipeline_id: frame.get_pipeline_id().to_string(),
                frame_number: *frame.get_frame_number(),
            };

            // FIXME: this must be changed, blocking the store does not allow to run several hooks at the same time. We clone stateless hooks for several frames
            //let mut store_mut = self.store.lock().unwrap();
            //info!("locked mutex");
            //let wasm_store_context = store_mut.as_context_mut();
            //info!("got mutable");
            match hook.interface0.call_hook(&mut store, &wasm_rgb_frame) {
                Ok(result_frame) => {
                    info!("Hook finished");
                    // FIXME: we must remove this copy of data from the wit data type to the rust defined type
                    let return_frame = pipeless::data::RgbFrame::from_values(
                        &result_frame.uuid, convert_to_array_3d(result_frame.original), convert_to_array_3d(result_frame.modified),
                        result_frame.width as usize, result_frame.height as usize,
                        result_frame.pts, result_frame.dts, result_frame.duration, result_frame.fps, result_frame.input_ts,
                        convert_to_array_3d_dyn(result_frame.inference_input), convert_to_array_3d_dyn(result_frame.inference_output),
                        &result_frame.pipeline_id, pipeless::data::UserData::Empty, // FIXME: update the user_data once supported
                        result_frame.frame_number
                    );
                    drop(store);
                    return Some(pipeless::data::Frame::RgbFrame(return_frame));
                },
                Err(err) => {
                    error!("Error executing Wasm hook: {}", err);
                    drop(store);
                    return None;
                }
            }
        } else {
            error!("The provided frame was not an RgbFrame");
            return None;
        }
    }
}

fn convert_to_vec_3d<A, D>(array: ndarray::ArrayBase<ndarray::OwnedRepr<A>, D>) -> Vec<Vec<Vec<A>>>
where
    A: Clone + std::fmt::Debug,
    D: ndarray::Dimension + ndarray::RemoveAxis,
{

    let shape = array.shape().to_owned();
    if shape.len() == 3 {
        let result: Vec<Vec<Vec<A>>> = array.into_raw_vec()
            .chunks(shape[1] * shape[2])
            .map(|chunk| {
                chunk
                    .chunks(shape[2])
                    .map(|row| {
                        row.to_vec()
                    })
                    .collect()
            })
            .collect();
        result
    } else {
        vec![vec![vec![]]]
    }
}

fn convert_to_array_3d<A>(vec: Vec<Vec<Vec<A>>>) -> ndarray::Array3<A>
where
    A: Clone + std::fmt::Debug + Default,
{
    error!("converting");
    let shape = [
        vec.len(),
        vec[0].len(),
        vec[0][0].len(),
    ];

    error!("{:?}", shape);

    if shape.len() == 3 {
        ndarray::ArrayBase::from_shape_fn(shape, |(row, col, channel)| vec[row][col][channel].clone())
    } else {
        let shape = [0, 0, 0];
        ndarray::Array3::default(shape)
    }
}

fn convert_to_array_3d_dyn<A>(vec: Vec<Vec<Vec<A>>>) -> ndarray::ArrayBase<ndarray::OwnedRepr<A>, ndarray::Dim<ndarray::IxDynImpl>>
where
    A: Clone,
{
    let dim = [
        vec.len(),
        vec.get(0).map_or(0, |inner| inner.len()),
        vec.get(0).and_then(|inner| inner.get(0)).map_or(0, |innermost| innermost.len()),
    ];

    let dim_dyn = ndarray::IxDyn(&[dim[0], dim[1], dim[2]]);
    ndarray::ArrayBase::from_shape_fn(dim_dyn, |dim_dyn| vec[dim_dyn[0]][dim_dyn[1]][dim_dyn[2]].clone())
}
