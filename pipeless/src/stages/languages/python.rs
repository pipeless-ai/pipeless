use std::collections::HashMap;
use log::{error, warn};
use pyo3::{PyObject, prelude::*};
use numpy::{self, ToPyArray};

use crate::{data::{Frame, InferenceOutput, RgbFrame, UserData}, kvs::store, stages::{hook::{HookTrait, HookType}, stage::{Context, ContextTrait}}};

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
    fn into_py(mut self, py: Python) -> Py<PyAny> {
        let dict = pyo3::types::PyDict::new(py);
        dict.set_item("uuid", self.get_uuid().to_string()).unwrap();
        dict.set_item("original", self.get_original_pixels().to_pyarray(py)).unwrap();
        dict.set_item("modified", self.get_modified_pixels().to_pyarray(py)).unwrap();
        dict.set_item("width", self.get_width()).unwrap();
        dict.set_item("height", self.get_height()).unwrap();
        dict.set_item("pts", self.get_pts().mseconds()).unwrap();
        dict.set_item("dts", self.get_dts().mseconds()).unwrap();
        dict.set_item("duration", self.get_duration().mseconds()).unwrap();
        dict.set_item("fps", self.get_fps()).unwrap();
        dict.set_item("input_ts", self.get_input_ts()).unwrap();
        dict.set_item("inference_input", self.get_inference_input().to_pyarray(py)).unwrap();
        match self.get_inference_output() {
            crate::data::InferenceOutput::Default(out) => {
                dict.set_item("inference_output", out.to_pyarray(py)).unwrap();
            },
            crate::data::InferenceOutput::OnnxInferenceOutput(out) => {
                let out_dict = pyo3::types::PyDict::new(py);
                for (key, value) in out {
                    out_dict.set_item(key, value.to_pyarray(py)).unwrap();
                }
                dict.set_item("inference_output", out_dict).unwrap();
            },
        };

        dict.set_item("pipeline_id", self.get_pipeline_id().to_string()).unwrap();
        dict.set_item("user_data", self.get_user_data()).unwrap();
        dict.set_item("frame_number", self.get_frame_number()).unwrap();
        dict.into()
    }
}

// Allows the RgbFrame variant of Frame to be converted from Python to Rust
impl<'source> FromPyObject<'source> for RgbFrame {
    fn extract(ob: &'source PyAny) -> PyResult<Self> {
        let original_py_array: &numpy::PyArray3<u8> = ob.get_item("original")?.downcast::<numpy::PyArray3<u8>>()?;
        let original_ndarray: ndarray::Array3<u8> = original_py_array.to_owned_array();
        let modified_py_array: &numpy::PyArray3<u8> = ob.get_item("modified")?.downcast::<numpy::PyArray3<u8>>()?;
        let modified_ndarray: ndarray::Array3<u8> = modified_py_array.to_owned_array();

        // TODO: support several inference inputs like for the runtimes. See how we use the inference output below
        let inference_input_ndarray: ndarray::ArrayBase<_, ndarray::Dim<ndarray::IxDynImpl>>;
        if let Ok(inference_input_py_array) = ob.get_item("inference_input")?.extract() {
            let inference_input_py_array: &numpy::PyArrayDyn<f32> = inference_input_py_array;
            inference_input_ndarray = inference_input_py_array.to_owned_array().into_dyn();
        } else {
            return Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>("Unable to obtain data from 'inference_input'. Is it a NumPy array of float values? Hint: use .astype('float32') in your Python code"));
        }

        let inference_output = if ob.get_item("inference_output")?.is_instance_of::<pyo3::types::PyDict>() {
            let dict = ob.get_item("inference_output")?.downcast::<pyo3::types::PyDict>()?;
            let dict_keys = dict.keys();
            let mut dict_items = HashMap::new();
            for key in dict_keys {
                let key_str = key.extract::<String>()?;
                let value = dict.get_item(key)?;
                match value {
                    Some(v) => {
                        let array = match v.extract::<&numpy::PyArray<f32, ndarray::Dim<ndarray::IxDynImpl>>>() {
                            Ok(v) => {
                                let inference_output_ndarray: ndarray::ArrayBase<_, ndarray::Dim<ndarray::IxDynImpl>> = v.to_owned_array().into_dyn();
                                inference_output_ndarray
                            },
                            Err(err) => {
                                warn!("Could not downcast Python object to PyArray. {}. Is it a NumPy array of float values? Hint: use .astype('float32') in your Python code", err.to_string());
                                ndarray::ArrayBase::zeros(ndarray::IxDyn(&[]))
                            }
                        };
                        dict_items.insert(key_str, array);
                    },
                    None => { dict_items.insert(key_str, ndarray::ArrayBase::zeros(ndarray::IxDyn(&[]))); },
                }
            }
            crate::data::InferenceOutput::OnnxInferenceOutput(dict_items)
        } else if let Ok(inference_output_py_array) = ob.get_item("inference_output")?.extract() {
            let inference_output_py_array: &numpy::PyArrayDyn<f32> = inference_output_py_array;
            let inference_output_ndarray: ndarray::ArrayBase<_, ndarray::Dim<ndarray::IxDynImpl>> = inference_output_py_array.to_owned_array().into_dyn();
            InferenceOutput::Default(inference_output_ndarray)
        } else {
            warn!("Unable to obtain data from 'inference_output'. Ensure it is either a dict of numpy arrays of float32 values or a NumPy array of float32 values. Hint: use .astype('float32') in your Python code");
            InferenceOutput::Default(ndarray::ArrayBase::zeros(ndarray::IxDyn(&[0])))
        };

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
        let inference_output = inference_output;
        let pipeline_id = ob.get_item("pipeline_id").unwrap().extract()?;
        let user_data = ob.get_item("user_data").unwrap().extract()?;
        let frame_number = ob.get_item("frame_number").unwrap().extract()?;

        let frame = RgbFrame::from_values(
            uuid, original, modified, width, height,
            pts, dts, duration, fps, input_ts,
            inference_input, inference_output,
            pipeline_id, user_data, frame_number
        );

        Ok(frame)
    }
}

/// Allows to pass the user data to python and back
impl ToPyObject for UserData {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        match self {
            UserData::Empty => py.None(),
            UserData::Integer(i) => i.into_py(py),
            UserData::Float(f) => f.into_py(py),
            UserData::String(s) => s.into_py(py),
            UserData::Array(arr) => {
                let list = pyo3::types::PyList::empty(py);
                for item in arr {
                    list.append(item.to_object(py)).unwrap();
                }
                list.into_py(py)
            }
            UserData::Dictionary(dict) => {
                let py_dict = pyo3::types::PyDict::new(py);
                for (key, value) in dict {
                    py_dict.set_item(key, value.to_object(py)).unwrap();
                }
                py_dict.into_py(py)
            }
        }
    }
}

/// Allows to pass the user data to python and back
impl<'source> FromPyObject<'source> for UserData {
    fn extract(obj: &'source PyAny) -> PyResult<Self> {
        if let Ok(integer) = obj.extract::<i32>() {
            Ok(UserData::Integer(integer))
        } else if let Ok(float) = obj.extract::<f64>() {
            Ok(UserData::Float(float))
        } else if let Ok(string) = obj.extract::<String>() {
            Ok(UserData::String(string))
        } else if obj.is_instance_of::<pyo3::types::PyList>() {
            let array = obj.downcast::<pyo3::types::PyList>()?;
            let array_data = array.into_iter()
                .map(|elem| UserData::extract(elem))
                .collect::<PyResult<Vec<UserData>>>()?;
            Ok(UserData::Array(array_data))
        } else if obj.is_instance_of::<pyo3::types::PyDict>() {
            let dict = obj.downcast::<pyo3::types::PyDict>()?;
            let dict_keys = dict.keys();
            let mut dict_items = Vec::new();
            for key in dict_keys {
                let key_str = key.extract::<String>()?;
                let value = dict.get_item(key)?;
                match value {
                    Some(v) => {
                        let value_data = UserData::extract(v)?;
                        dict_items.push((key_str, value_data));
                    },
                    None => { dict_items.push((key_str, UserData::Empty)); },
                }
            }
            Ok(UserData::Dictionary(dict_items))
        } else if obj.is_none() {
            Ok(UserData::Empty)
        } else {
            Err(pyo3::exceptions::PyTypeError::new_err("Unsupported data type assigned to 'user_data'. Please check in the Pipeless the supported types."))
        }
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
    pub fn new(hook_type: HookType, stage_name: &str,py_code: &str) -> Self {
        // The wrapper removes the need for the user to return a frame from each hook
        // Also, injects the set and get functions for the KV store namespacing the keys
        // to avoid conflicts between streams in the format stage_name:pipeline_id:user_provided_key
        // Since all executions share the Python interpreter, we have to create different names for
        // all the modules
        let module_name = format!("_{}_{}", stage_name, hook_type); // Prepend with underscore to allow modules starting with numbers
        let module_file_name = format!("{}.py", module_name);
        let wrapper_module_name = format!("{}_wrapper", module_name);
        let wrapper_module_file_name = format!("{}.py", wrapper_module_name);
        // NOTE: We prepend the keys with the pipeline id and the stage name. The stage avoids key collision when you import a stage from the hub. We set the pipeline_id first to make it easier to cleanup when a stream ends
        // TODO: create a KVS module for python using PYo3 and expose it via pyo3::append_to_inittab!(make_person_module); so users can import it on their hooks
        let wrapper_py_code = format!("
import {0}

def hook_wrapper(frame, context):
    pipeline_id = frame['pipeline_id']
    def pipeless_kvs_set(key, value):
        _pipeless_kvs_set(f'{{pipeline_id}}:{1}:{{key}}', str(value))
    def pipeless_kvs_get(key):
        return _pipeless_kvs_get(f'{{pipeline_id}}:{1}:{{key}}')
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
    fn exec_hook(&self, mut frame: Frame, _stage_context: &Context) -> Option<Frame> {
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
                let original_pixels = frame.get_original_pixels().to_owned(); // it seems that to_owned implies to copy data
                // TODO: we will probably need a pool of interpreters to avoid initializing a new one ever time because o cold starts
                // TODO: this acquires the Python GIL, breaking the concurrency, except when we are running on different cores thanks
                //       to how we invoke frame processing using the Tokio thread pool, becuase it runs threads on all the cores.
                // See: Follow this to run async code in python even with GIL: https://pyo3.rs/v0.11.1/parallelism
                match hook_func.call1(py, (frame, stage_context.into_py(py),)) {
                    Ok(ret) => {
                        match ret.extract::<Frame>(py) {
                            Ok(mut f) => {
                                // Avoid the user to accidentally modify the original frame
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
