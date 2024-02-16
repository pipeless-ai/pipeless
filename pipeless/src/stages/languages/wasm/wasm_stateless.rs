use log::error;
use wasmtime;
use crate as pipeless;
use crate::{data::Frame, stages::hook::{HookTrait, HookType}};
use std::cell::RefCell;
use wasmtime::AsContextMut;

// To implement WASM stateless hooks we instance a component per thread, so we can call each component with its associated mutable store.
// Also, that allows us to mutate the store (which is required by wasmtime) because a thread won't execute two components at the same time
// By using a store per hook we could eventually unload hooks and droping the store the hook memory would be released. If we
// create a single store for all hooks, since there is not GC for a store, the memory would never be released
pub struct ThreadBoundComponent {
    store: wasmtime::Store<super::ServerWasiView>,
    hook: super::HookComponent, // This is the bingen generated hook.
}

// In order to maintain several omponents per thread and being able to create them only when required (to save memory)
// this hashmap contains stage_name_hook_type prefixed components bounded to the execution thread
// When parsing the user hooks and stages we populate the hashmap per thread
type ThreadBoundComponents = std::collections::HashMap<String, ThreadBoundComponent>;
thread_local! {
    pub static THREAD_COMPONENTS: RefCell<ThreadBoundComponents> = RefCell::new(std::collections::HashMap::new());
}

pub struct WasmStatelessHook {
    component_hashmap_key: String,
    component: wasmtime::component::Component,
}
impl WasmStatelessHook {
    pub fn new(hook_type: HookType, stage_name: &str, component: &wasmtime::component::Component) -> Self {
        Self {
            component_hashmap_key: format!("{}_{}", stage_name, hook_type.to_string()),
            component: component.clone(), // We can clone this because is just the wasm parsed file
        }
    }
}
impl HookTrait for WasmStatelessHook {
    fn exec_hook(&self, frame: Frame, stage_context: &pipeless::stages::stage::Context) -> Option<Frame> {

        // FIXME: Use the stage context. We have to resolve the type to use since we cannot create dictionaries as it requires recursive types
        //let stage_context = match stage_context {
        //    crate::stages::stage::Context::WasmContext(wasm_context) => wasm_context,
        //    crate::stages::stage::Context::EmptyContext => &super::WasmStageContext::new(0),
        //    _ =>  {
        //        error!("The stage context provided to the Wasm executor is not a Wasm context. Defaulting to empty context to avoid failure.");
        //        &super::WasmStageContext::new(0)
        //    }
        //};

        // If this thread does not have a component instantiated, instantiate one. This would be equivalent to create a component bounded to
        // the tokio threadpool thread.
        THREAD_COMPONENTS.with(|components| {
            let mut components_mut = components.borrow_mut();
            if let Some(thread_bound_component) = components_mut.get_mut(&self.component_hashmap_key) {
                error!("Running stateless hook with existing component");
                return process_frame(thread_bound_component, frame);
            } else {
                error!("Creating component for stateless hook");
                let mut linker = wasmtime::component::Linker::new(&pipeless::components::engine::WASM_ENGINE.get_engine());
                wasmtime_wasi::preview2::command::sync::add_to_linker(&mut linker).unwrap();
                let wasi_view = super::ServerWasiView::new();
                let mut store = wasmtime::Store::new(&pipeless::components::engine::WASM_ENGINE.get_engine(), wasi_view);
                let (hook, _component_instance) = super::HookComponent::instantiate(&mut store, &self.component, &linker).unwrap();
                let mut thread_bound_component = ThreadBoundComponent { hook, store };
                error!("Running stateless hook");
                let result_frame = process_frame(&mut thread_bound_component, frame);
                error!("Finished stateless hook, storing in hashmap");
                components_mut.insert(self.component_hashmap_key.clone(), thread_bound_component);
                return result_frame;
            }
        })
    }
}

fn process_frame(component: &mut ThreadBoundComponent, frame: Frame,) -> Option<Frame> {
    if let pipeless::data::Frame::RgbFrame(mut frame) = frame {
        // FIXME: we must avoid this copy from the Rust struct to the Wit defined data type
        let wasm_rgb_frame = super::exports::pipeless_wasm::hooks::hook_interface::WasmRgbFrame {
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

        match component.hook.pipeless_wasm_hooks_hook_interface().call_hook(component.store.as_context_mut(), &wasm_rgb_frame) {
            Ok(result_frame) => {
                // FIXME: we must remove this copy of data from the wit data type to the rust defined type
                let return_frame = pipeless::data::RgbFrame::from_values(
                    &result_frame.uuid, convert_to_array_3d(result_frame.original), convert_to_array_3d(result_frame.modified),
                    result_frame.width as usize, result_frame.height as usize,
                    result_frame.pts, result_frame.dts, result_frame.duration, result_frame.fps, result_frame.input_ts,
                    convert_to_array_3d_dyn(result_frame.inference_input), convert_to_array_3d_dyn(result_frame.inference_output),
                    &result_frame.pipeline_id, pipeless::data::UserData::Empty, // FIXME: update the user_data once supported
                    result_frame.frame_number
                );
                //drop(store);
                return Some(pipeless::data::Frame::RgbFrame(return_frame));
            },
            Err(err) => {
                error!("Error executing Wasm hook: {}", err);
                //drop(store);
                return None;
            }
        }
    } else {
        error!("The provided frame was not an RgbFrame");
        return None;
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
    let shape = [
        vec.len(),
        vec[0].len(),
        vec[0][0].len(),
    ];

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
