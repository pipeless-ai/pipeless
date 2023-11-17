use log::{error, warn};
use pyo3::prelude::*;
use numpy::{self, ToPyArray};

use crate::{data::{RgbFrame, Frame}, stages::{hook::HookTrait, stage::ContextTrait}, stages::stage::Context, kvs::store};

/// Allows a Frame to be converted from Rust to Python
impl IntoPy<Py<PyAny>> for Frame {
    fn into_py(self, py: Python) -> Py<PyAny> {
        match self {
            Frame::RgbFrame(frame) => frame.into_py(py),
        }
    }
}
/// Allows the Frame to be converted from Python to Rust
impl<'source> FromPyObject<'source> for Frame {
    fn extract(ob: &'source PyAny) -> PyResult<Self> {
        match RgbFrame::extract(ob) {
            Ok(frame) => Ok(Frame::RgbFrame(frame)),
            Err(err) => {
                error!("Unable to convert Python object to any known Frame variant {}", err);
                Err(err)
            }
        }
    }
}
/// Allows the RgbFrame variant of Frame to be converted from Rust to Python
impl IntoPy<Py<PyAny>> for RgbFrame {
    fn into_py(self, py: Python) -> Py<PyAny> {
        let dict = pyo3::types::PyDict::new(py);
        dict.set_item("uuid", self.get_uuid().to_string()).unwrap();
        dict.set_item("original", numpy::PyArray3::from_owned_array(py, self.get_owned_original_pixels())).unwrap();
        dict.set_item("modified", numpy::PyArray3::from_owned_array(py, self.get_owned_modified_pixels())).unwrap();
        dict.set_item("width", self.get_width()).unwrap();
        dict.set_item("height", self.get_height()).unwrap();
        dict.set_item("pts", self.get_pts().mseconds()).unwrap();
        dict.set_item("dts", self.get_dts().mseconds()).unwrap();
        dict.set_item("duration", self.get_duration().mseconds()).unwrap();
        dict.set_item("fps", self.get_fps()).unwrap();
        dict.set_item("input_ts", self.get_input_ts().elapsed().as_millis()).unwrap();
        dict.set_item("inference_input", self.get_inference_input().to_owned().to_pyarray(py)).unwrap();
        dict.set_item("inference_output", self.get_inference_output().to_owned().to_pyarray(py)).unwrap();
        dict.set_item("pipeline_id", self.get_pipeline_id().to_string()).unwrap();
        dict.into()
    }
}
/// Allows the RgbFrame variant of Frame to be converted from Python to Rust
impl<'source> FromPyObject<'source> for RgbFrame {
    fn extract(ob: &'source PyAny) -> PyResult<Self> {
        let original_py_array: &numpy::PyArray3<u8> = ob.get_item("original")?.extract()?;
        let original_ndarray: ndarray::Array3<u8> = original_py_array.to_owned_array();
        let modified_py_array: &numpy::PyArray3<u8> = ob.get_item("modified")?.extract()?;
        let modified_ndarray: ndarray::Array3<u8> = modified_py_array.to_owned_array();

        let inference_input_ndarray: ndarray::ArrayBase<_, ndarray::Dim<ndarray::IxDynImpl>>;
        if let Ok(inference_input_py_array) = ob.get_item("inference_input")?.extract() {
            let inference_input_py_array: &numpy::PyArrayDyn<f32> = inference_input_py_array;
            inference_input_ndarray = inference_input_py_array.to_owned_array().into_dyn();
        } else {
            return Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>("Unable to obtain data from 'inference_input'. Is it a NumPy array of float values? Hint: use .astype('float32') in your Python code"));
        }

        let inference_output_ndarray: ndarray::ArrayBase<_, ndarray::Dim<ndarray::IxDynImpl>>;
        if let Ok(inference_output_py_array) = ob.get_item("inference_output")?.extract() {
            let inference_output_py_array: &numpy::PyArrayDyn<f32> = inference_output_py_array;
            inference_output_ndarray = inference_output_py_array.to_owned_array().into_dyn();
        } else {
            return Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>("Unable to obtain data from 'inference_output'. Is it a NumPy array of float values? Hint: use .astype('float32') in your Python code"));
        }

        let uuid = ob.get_item("uuid").unwrap().extract()?;
        let original = original_ndarray;
        let modified = modified_ndarray;
        let width = ob.get_item("width").unwrap().extract()?;
        let height = ob.get_item("height").unwrap().extract()?;
        let pts = ob.get_item("pts").unwrap().extract()?;
        let dts = ob.get_item("dts").unwrap().extract()?;
        let duration = ob.get_item("duration").unwrap().extract()?;
        let fps = ob.get_item("fps").unwrap().extract()?;
        let input_ts = ob.get_item("input_ts").unwrap().extract()?;
        let inference_input = inference_input_ndarray;
        let inference_output =inference_output_ndarray;
        let pipeline_id = ob.get_item("pipeline_id").unwrap().extract()?;

        let frame = RgbFrame::from_values(
            uuid, original, modified, width, height,
            pts, dts, duration, fps, input_ts,
            inference_input, inference_output,
            pipeline_id,
        );

        Ok(frame)
    }
}

/// Python context to maintain within a stage
pub struct PythonStageContext {
    context: Py<pyo3::types::PyDict>,
}
impl ContextTrait<PythonStageContext> for PythonStageContext {
    fn init_context(stage_name: &str, init_code: &str) -> Self {
        let module_name = format!("{}_{}", stage_name, "init");
        let module_file_name = format!("{}.py", module_name);
        let py_ctx = Python::with_gil(|py| -> Py<pyo3::types::PyDict> {
            let init_module = pyo3::types::PyModule::from_code(
                py, init_code, &module_file_name, &module_name
            ).expect("Unable to create Python module from init hook");

            if let Ok(init_func) = init_module.getattr("init") {
                let args = pyo3::types::PyTuple::empty(py);
                match init_func.call1(args) {
                    Ok(ret) => {
                        let py_dict: &pyo3::types::PyDict = ret.downcast()
                            .expect("Unable to cast returned dict to Python dict");
                        return py_dict.into();
                    },
                    Err(err) => {
                        error!("Error executing stage init: {}", err);
                        warn!("Defaulting to use of an empty stage context");
                        return pyo3::types::PyDict::new(py).into();
                    }
                };
            } else {
                error!("Cannot find 'init' function at init.py for stage '{}'. Defaulting to empty stage context", stage_name);
                pyo3::types::PyDict::new(py).into()
            }
        });
        PythonStageContext { context: py_ctx }
    }
}
/// Allow to convert from Rust to Python
impl IntoPy<Py<PyAny>> for &PythonStageContext {
    fn into_py(self, py: Python) -> Py<PyAny> {
        // NOTE: here the context is being cloned. The user should not
        //       modify the context after initialized, because it won't take effect
        //       for other frames
        self.context.clone().into_py(py)
    }
}

/// Defines a Hook implemented in Python
pub struct PythonHook {
    module: Py<pyo3::types::PyModule>,
}
impl PythonHook {
    pub fn new(stage_name: &str, hook_type: &str, py_code: &str) -> Self {
        // The wrapper removes the need for the user to return a frame from each hook
        // Also, injects the set and get functions for the KV store namespacing the keys
        // to avoid conflicts between streams in the format stage_name:pipeline_id:user_provided_key
        // Since all executions share the Python interpreter, we have to create different names for
        // all the modules
        let module_name = format!("{}_{}", stage_name, hook_type);
        let module_file_name = format!("{}.py", module_name);
        let wrapper_module_name = format!("{}_wrapper", module_name);
        let wrapper_module_file_name = format!("{}.py", wrapper_module_name);
        let wrapper_py_code = format!("
import {0}

def hook_wrapper(frame, context):
    pipeline_id = frame['pipeline_id']
    def pipeless_kvs_set(key, value):
        _pipeless_kvs_set(f'{1}:{{pipeline_id}}:{{key}}', str(value))
    def pipeless_kvs_get(key):
        return _pipeless_kvs_get(f'{1}:{{pipeline_id}}:{{key}}')
    {0}.pipeless_kvs_set = pipeless_kvs_set
    {0}.pipeless_kvs_get = pipeless_kvs_get
    {0}.hook(frame, context)
    return frame
", module_name, stage_name);
        let module = Python::with_gil(|py| -> Py<pyo3::types::PyModule> {
            // Create the hook module from user code
            let hook_module = pyo3::types::PyModule::from_code(
                py, py_code, &module_file_name, &module_name
            ).expect("Unable to create Python module from hook");

            // Create the wrapper module
            let wrapper_module = pyo3::types::PyModule::from_code(
                py, &wrapper_py_code, &wrapper_module_file_name, &wrapper_module_name
            ).expect("Unable to create wrapper Python module");
            // Add some util functions that the user can invoke from the Python code
            #[pyfunction]
            fn _pipeless_kvs_set(key: &str, value: &str) {
                store::KV_STORE.set(key, value);
            }
            #[pyfunction]
            fn _pipeless_kvs_get(key: &str) -> String {
                store::KV_STORE.get(key)
            }
            wrapper_module.add_function(wrap_pyfunction!(_pipeless_kvs_set, wrapper_module).unwrap()).expect("Failed to inject KV store set function");
            wrapper_module.add_function(wrap_pyfunction!(_pipeless_kvs_get, wrapper_module).unwrap()).expect("Failed to inject KV store get function");
            wrapper_module.add(&module_name, hook_module).expect("Failed to inject Python hook module into wrapper module");
            wrapper_module.into()
        });

        Self { module }
    }
    pub fn get_module(&self) -> &Py<pyo3::types::PyModule> {
        &self.module
    }
}
impl HookTrait for PythonHook {
    /// Executes a Python hook by obtaining the GIL and passes the provided frame and stage context to it
    fn exec_hook(&self, frame: Frame, _stage_context: &Context) -> Option<Frame> {
        let py_module = self.get_module();
        let out_frame = Python::with_gil(|py| -> Option<Frame> {
            let stage_context = match _stage_context {
                crate::stages::stage::Context::PythonContext(python_context) => python_context.into_py(py),
                crate::stages::stage::Context::EmptyContext => pyo3::types::PyDict::new(py).into_py(py),
                _ =>  {
                    error!("The stage context provided to the Python executor is not a Python context. Defaulting to empty context to avoid failure.");
                    pyo3::types::PyDict::new(py).into_py(py)
                }
            };

            if let Ok(hook_func) = py_module.getattr(py, "hook_wrapper") {
                let original_pixels = frame.get_original_pixels().to_owned();
                // TODO: we will probably need a pool of interpreters to avoid initializing a new one ever time because o cold starts
                // TODO: this acquires the Python GIL, breaking the concurrency, except when we are running on different cores thanks
                //       to how we invoke frame processing using the Tokio thread pool, becuase it runs threads on all the cores.
                // See: Follow this to run async code in python even with GIL: https://pyo3.rs/v0.11.1/parallelism
                match hook_func.call1(py, (frame, stage_context.into_py(py),)) {
                    Ok(ret) => {
                        match ret.extract::<Frame>(py) {
                            Ok(mut f) => {
                                // Avoid the user to accidentally the original frame
                                f.set_original_pixels(original_pixels);
                                return Some(f)
                            },
                            Err(err) => {
                                error!("Error executing Python hook: {}", err);
                                return None
                            },
                        }
                    },
                    Err(err) => {
                        error!("Error executing hook: {}", err);
                       return None
                    }
                };
            } else {
                error!("'hook' function not found in hook module. Skipping execution");
                return None
            }
        });

        out_frame
    }
}