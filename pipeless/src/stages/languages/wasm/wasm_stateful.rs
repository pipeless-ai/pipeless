use std::sync::{Arc, Mutex};
use std::time::Instant;

use log::{error, warn};
use wasmtime::AsContextMut;
use crate as pipeless;
use crate::{data::Frame, stages::hook::{HookTrait, HookType}};

pub struct WasmStatefulHook {
    store: Arc<Mutex<wasmtime::Store<super::ServerWasiView>>>,
    hook: super::HookComponent, // This is the bingen generated hook.
}
impl WasmStatefulHook {
    pub fn new(_hook_type: HookType, _stage_name: &str, component: &wasmtime::component::Component) -> Self {
        // FIXME: is there any way we can prefix the component with the stage name and hook type for traceability like we do in python?
        let mut linker = wasmtime::component::Linker::new(&pipeless::components::engine::WASM_ENGINE.get_engine());
        wasmtime_wasi::preview2::command::sync::add_to_linker(&mut linker).unwrap();
        let wasi_view = super::ServerWasiView::new();
        let mut store = wasmtime::Store::new(&pipeless::components::engine::WASM_ENGINE.get_engine(), wasi_view);
        let (hook, _component_instance) = super::HookComponent::instantiate(&mut store, &component, &linker).unwrap();

        Self {
            store: Arc::new(Mutex::new(store)),
            hook,
        }
    }
}
impl HookTrait for WasmStatefulHook {
    fn exec_hook(&self, frame: Frame, stage_context: &pipeless::stages::stage::Context) -> Option<Frame> {
        // FIXME: Use the stage context. We have to resolve the type to use since we cannot create dictionaries as it requires recursive types
        //let wasm_stage_ctx = super::wasm::WasmStageContext::new(0);
        //let stage_context = match stage_context {
        //    crate::stages::stage::Context::WasmContext(wasm_context) => wasm_context,
        //    crate::stages::stage::Context::EmptyContext => &wasm_stage_ctx,
        //    _ =>  {
        //        error!("The stage context provided to the Wasm executor is not a Wasm context. Defaulting to empty context to avoid failure.");
        //        &wasm_stage_ctx
        //    }
        //};

        // This if allows us to extend the frame variants in the future
        if let pipeless::data::Frame::RgbFrame(mut frame) = frame {
            // FIXME: we must avoid this copy from the Rust struct to the Wit defined data type
            let t_start = Instant::now();
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
            let t_end = std::time::Instant::now();
            let duration = t_end - t_start;
            println!("Complete frame conversion took: {:?}", duration);

            if let Ok(mut store) = self.store.lock() {
                // FIXME: copying the frame to the wasm memory and back takes too long
                match self.hook.pipeless_wasm_hooks_hook_interface().call_hook(store.as_context_mut(), &wasm_rgb_frame) {
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
                        return Some(pipeless::data::Frame::RgbFrame(return_frame));
                    },
                    Err(err) => {
                        error!("Error executing Wasm hook: {}", err);
                        return None;
                    }
                }
            } else {
                warn!("Could not lock wasm store mutex, skipping frame processing");
                return None
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
    let t_start = Instant::now();

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

            let t_end = std::time::Instant::now();
            let duration = t_end - t_start;
            println!("ArrayBase to 3D vector took: {:?}", duration);

        result
    } else {
        vec![vec![vec![]]]
    }
}

fn convert_to_array_3d<A>(vec: Vec<Vec<Vec<A>>>) -> ndarray::Array3<A>
where
    A: Clone + std::fmt::Debug + Default,
{
    let t_start = Instant::now();
    let shape = [
        vec.len(),
        vec[0].len(),
        vec[0][0].len(),
    ];

    if shape.len() == 3 {
        let result = ndarray::ArrayBase::from_shape_fn(shape, |(row, col, channel)| vec[row][col][channel].clone());
        let t_end = std::time::Instant::now();
        let duration = t_end - t_start;
        println!("3D vector to Array3 took: {:?}", duration);
        result
    } else {
        let shape = [0, 0, 0];
        ndarray::Array3::default(shape)
    }
}

fn convert_to_array_3d_dyn<A>(vec: Vec<Vec<Vec<A>>>) -> ndarray::ArrayBase<ndarray::OwnedRepr<A>, ndarray::Dim<ndarray::IxDynImpl>>
where
    A: Clone,
{
    let t_start = Instant::now();
    let dim = [
        vec.len(),
        vec.get(0).map_or(0, |inner| inner.len()),
        vec.get(0).and_then(|inner| inner.get(0)).map_or(0, |innermost| innermost.len()),
    ];

    let dim_dyn = ndarray::IxDyn(&[dim[0], dim[1], dim[2]]);
    let result = ndarray::ArrayBase::from_shape_fn(dim_dyn, |dim_dyn| vec[dim_dyn[0]][dim_dyn[1]][dim_dyn[2]].clone());
    let t_end = std::time::Instant::now();
    let duration = t_end - t_start;
    println!("3D vector to DynArrayBase took: {:?}", duration);
    result
}
