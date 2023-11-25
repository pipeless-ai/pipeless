use log::{error, warn};
use ort;

use crate as pipeless;

pub struct OnnxSessionParams {
    stage_name: String, // Name o the stage this session belongs to
    execution_provider: String, //The user has to provide the execution provider
    execution_mode: Option<String>, // Parallel or sequential exeuction mode or onnx
    inter_threads: Option<i16>, // If execution mode is Parallel (and nodes can be run in parallel), this sets the maximum number of threads to use to run them in parallel.
    intra_threads: Option<i16>, // Number of threads to parallelize the execution within nodes
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
        inter_threads: Option<i16>, intra_threads: Option<i16>
    ) -> Self {
        Self {
            stage_name: stage_name.to_string(),
            execution_provider: execution_provider.to_string(),
            execution_mode: execution_mode.map(|m| m.to_string()),
            inter_threads, intra_threads,
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

            let session = session_builder.with_model_from_file(model_file_path).unwrap();

            // Run a first test inference that usually takes more time.
            // This avoids to add an initial delay to the stream when it arrives, making the session ready
            let input0_shape: Vec<usize> = session.inputs[0].dimensions()
                .map(std::option::Option::unwrap)
                .collect();
            // Assuming the conventional input format: batch, channels, height, witdh
            let batch_shift = if input0_shape.len() > 3 { 1 } else { 0 };
            let width = input0_shape[2 + batch_shift];
            let height = input0_shape[1 + batch_shift];
            let channels = input0_shape[0 + batch_shift];
            let test_image = ndarray::Array3::<u8>::zeros((channels, height, width)).into_dyn();
            let cow_array = ndarray::CowArray::from(test_image);
            let ort_input_value = ort::Value::from_array(
                session.allocator(),
                &cow_array
            ).unwrap();
            let _ = session.run(vec![ort_input_value]);

            Ok(Self { session })
        } else {
            let err = "Wrong parameters provided to ONNX session";
            Err(err.to_owned())
        }
    }
}

impl super::session::SessionTrait for OnnxSession {
    fn infer(&self, mut frame: pipeless::data::Frame) -> pipeless::data::Frame {
        let input_data = frame.get_inference_input().to_owned();
        if input_data.len() == 0 {
            warn!("No inference input data was provided. Did you forget to add it at your pre-process hook?");
            return frame;
        }

        // TODO: automatically resize and traspose the input image to the expected by the model

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
                        // TODO: iterate over the outputs hashmap to return all the model outputs not just the first
                        let output = outputs[&self.session.outputs[0].name].try_extract().unwrap();
                        let output_ndarray = output.view().to_owned();
                        frame.set_inference_output(output_ndarray);
                    },
                    Err(err) => error!("There was an error running inference: {}", err)
                }
            },
            Err(err) => error!("There was an error creating the input tensor: {}", err)
        }

       frame
    }
}
