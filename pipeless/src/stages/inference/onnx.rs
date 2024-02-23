use std::collections::HashMap;

use log::{error, warn};
use ort;

use crate as pipeless;

pub type OnnxInferenceOutput = HashMap<String, ndarray::ArrayBase<ndarray::OwnedRepr<f32>, ndarray::Dim<ndarray::IxDynImpl>>>;

pub struct OnnxSessionParams {
    stage_name: String, // Name o the stage this session belongs to
    execution_provider: String, //The user has to provide the execution provider
    execution_mode: Option<String>, // Parallel or sequential exeuction mode or onnx
    inter_threads: Option<i16>, // If execution mode is Parallel (and nodes can be run in parallel), this sets the maximum number of threads to use to run them in parallel.
    intra_threads: Option<i16>, // Number of threads to parallelize the execution within nodes
    custom_op_lib_path: Option<String>, // Path to a custom op library
    /*ir_version: Option<u32>,
    opset_version: Option<u32>,
    image_shape_format: Option<Vec<String>>,
    image_width: Option<u32>,
    image_height: Option<u32>,
    image_channels: Option<u8>,*/
}
impl OnnxSessionParams {
    pub fn new(
        stage_name: &str,
        execution_provider: &str, execution_mode: Option<&str>,
        inter_threads: Option<i16>, intra_threads: Option<i16>,
        custom_op_lib_path: Option<&str>,
    ) -> Self {
        Self {
            stage_name: stage_name.to_string(),
            execution_provider: execution_provider.to_string(),
            execution_mode: execution_mode.map(|m| m.to_string()),
            inter_threads, intra_threads,
            custom_op_lib_path: custom_op_lib_path.map(|p| p.to_string()),
        }
    }
}
pub struct OnnxSession {
    session: ort::Session,
}
impl OnnxSession {
    pub fn new(model_uri: &str, params: super::session::SessionParams) -> Result<Self, String> {
        if let pipeless::stages::inference::session::SessionParams::Onnx(onnx_params) = params {
            let execution_provider = match onnx_params.execution_provider.as_str() {
                // TODO: support configurable options or each provider.
                "cpu" | "CPU" => ort::ExecutionProvider::CPU(Default::default()),
                "cuda" | "CUDA" => ort::ExecutionProvider::CUDA(Default::default()),
                "tensorrt" | "TENSORRT" | "TensorRT" => ort::ExecutionProvider::TensorRT(Default::default()),
                "openvino" | "OpenVINO" | "OpenVino" | "OPENVINO" => ort::ExecutionProvider::OpenVINO(Default::default()),
                "coreml" | "CoreML" | "CoreMl" | "COREML" => ort::ExecutionProvider::CoreML(Default::default()), // Only for MacOs
                // ort::ExecutionProvider::ACL(Default::default()),
                other => {
                    let err = format!("Unsupported execution provider for the ONNX Runtime: '{}'", other);
                    return Err(err);
                }
            };

            let model_file_path = super::util::get_model_path(model_uri, "main")?;
            let environment = ort::Environment::builder()
                .with_log_level(ort::LoggingLevel::Warning)
                .with_name(onnx_params.stage_name)
                .with_execution_providers([execution_provider])
                .build().unwrap()
                .into_arc();

            let mut session_builder = ort::SessionBuilder::new(&environment).unwrap();
            // Allow all optimizations by default (Level 3 is the highest)
            // TODO: make optimization level configurable
            session_builder = session_builder.with_optimization_level(ort::GraphOptimizationLevel::Level3).unwrap();
            if let Some(intra_threads) = onnx_params.intra_threads {
                session_builder = session_builder.with_intra_threads(intra_threads).unwrap();
            }
            if let Some(mode) = onnx_params.execution_mode {
                match mode.as_str() {
                    "parallel" | "Parallel" | "PARALLEL" => {
                        session_builder = session_builder.with_parallel_execution(true).unwrap();
                        if let Some(inter_threads) = onnx_params.inter_threads {
                            session_builder = session_builder.with_inter_threads(inter_threads).unwrap();
                        }
                    },
                    "sequential" | "Sequential" | "SEQUENTIAL" => {
                        session_builder = session_builder.with_parallel_execution(false).unwrap();
                    },
                    mode => {
                        return Err(format!("Unrecognized execution mode: {}", mode));
                    }
                }
            }

            if let Some(lib_path) = onnx_params.custom_op_lib_path {
                log::info!("Loading custom operations lib from: {}", lib_path);
                session_builder = session_builder.with_custom_op_lib(&lib_path).unwrap();
            }

            let session = session_builder.with_model_from_file(model_file_path).unwrap();

            // Run a first test inference that usually takes more time.
            // This avoids to add an initial delay to the stream when it arrives, making the session ready
            let input0_shape: Vec<Option<usize>> = session.inputs[0].dimensions().map(|x| x).collect();
            if input0_shape.len() > 2 {
                // Assuming the conventional input format: batch, channels, height, witdh
                let batch_shift = if input0_shape.len() > 3 { 1 } else { 0 };
                let width = input0_shape[2 + batch_shift];
                let height = input0_shape[1 + batch_shift];
                let channels = input0_shape[0 + batch_shift];
                if let (Some(width), Some(height), Some(channels)) = (width, height, channels) {
                    let test_image = ndarray::Array3::<u8>::zeros((channels, height, width)).into_dyn();
                    let cow_array = ndarray::CowArray::from(test_image);
                    let ort_input_value = ort::Value::from_array(
                        session.allocator(),
                        &cow_array
                    ).unwrap();
                    let _ = session.run(vec![ort_input_value]);
                } else {
                    warn!(
                        "Could not run an inference test because the model input shape was not properly recognized. Obtained: width: {:?}, height: {:?}, channels: {:?}",
                        width.map(|num| num.to_string()).unwrap_or_else(|| "None".to_string()), // Print the number on the option or "None"
                        height.map(|num| num.to_string()).unwrap_or_else(|| "None".to_string()),
                        channels.map(|num| num.to_string()).unwrap_or_else(|| "None".to_string())
                    );
                }
            } else {
                warn!("Could not run an inference test because the model input shape does not contain all the image dimensions");
            }

            Ok(Self { session })
        } else {
            let err = "Wrong parameters provided to ONNX session";
            Err(err.to_owned())
        }
    }
}

impl super::session::SessionTrait for OnnxSession {
    fn infer(&self, mut frame: pipeless::data::Frame) -> pipeless::data::Frame {
        // TODO: automatically resize and traspose the input image to the expected by the model

        // FIXME: we are forcing users to provide float32 arrays which will produce the inference to fail if the model expects uint values.

        let input_data = frame.get_inference_input().to_owned();
        if input_data.len() == 0 {
            warn!("No inference input data was provided. Did you forget to add it at your pre-process hook?");
            return frame;
        }

        let input_vec = input_data.view().insert_axis(ndarray::Axis(0)).into_dyn(); // Batch image with batch size 1
        let cow_array = ndarray::CowArray::from(input_vec);
        let ort_input_value_result = ort::Value::from_array(
            self.session.allocator(),
            &cow_array
        );
        match ort_input_value_result {
            Ok(ort_input_value) => {
                // Use IO bindings for faster data movement between devices
                let mut io_bindings = self.session.bind().unwrap();
                // TODO: support more than one model input
                let _ = io_bindings.bind_input(self.session.inputs[0].name.as_str(), ort_input_value).unwrap();

                for output in &self.session.outputs {
                    let output_mem_info = ort::MemoryInfo::new(
                        ort::AllocationDevice::CPU, 0, ort::AllocatorType::Device, ort::MemType::Default
                    ).unwrap();
                    let _ = io_bindings.bind_output(output.name.as_str(), output_mem_info).unwrap();
                }
                match self.session.run_with_binding(&io_bindings) {
                    Ok(()) => {
                        let outputs = io_bindings.outputs().unwrap();
                        let mut frame_inference_output = OnnxInferenceOutput::new();
                        for (output_name, output_value) in outputs {
                            // FIXME: the extract code is very unelegant. The extract can return several different numric types depending on the model used
                            //        and there is not a number wrapper that we can apply, so we have to check type by type
                            match output_value.try_extract() {
                                Ok(output) => {
                                    //let output = output.view().map(|v: &_| v.into());
                                    // FIXME: we can use an arrayview for the inference output instead of owned array base to avoid copying here.
                                    let output_ndarray = output.view().to_owned();
                                    frame_inference_output.insert(output_name, output_ndarray);
                                },
                                Err(_err) => {
                                    // Try to convert from i64 since sometimes the models do not return floats
                                    match output_value.try_extract() {
                                        Ok(output) => {
                                            // FIXME: this copies the array twice, first to_owned and then the mapv
                                            let output_ndarray: ndarray::ArrayBase<ndarray::OwnedRepr<i64>, _> = output.view().to_owned();
                                            let float_output = output_ndarray.mapv(|v| v as f32);
                                            frame_inference_output.insert(output_name, float_output);
                                        }
                                        Err(_err) => {
                                            // Try to convert from i64 since sometimes the models do not return floats
                                            match output_value.try_extract() {
                                                Ok(output) => {
                                                    // FIXME: this copies the array twice, first to_owned and then the mapv
                                                    let output_ndarray: ndarray::ArrayBase<ndarray::OwnedRepr<i32>, _> = output.view().to_owned();
                                                    let float_output = output_ndarray.mapv(|v| v as f32);
                                                    frame_inference_output.insert(output_name, float_output);
                                                }
                                                Err(err) => warn!("Error extracting inference results: {}", err.to_string()),
                                            }
                                        },
                                    }
                                }
                            }
                        }
                        frame.set_inference_output(pipeless::data::InferenceOutput::OnnxInferenceOutput(frame_inference_output));
                    },
                    Err(err) => error!("There was an error running inference: {}", err)
                }
            },
            Err(err) => error!("There was an error creating the input tensor: {}", err)
        }

       frame
    }
}
