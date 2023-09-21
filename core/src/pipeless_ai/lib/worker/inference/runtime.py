import sys
import numpy as np
import onnx
import onnxruntime

from pipeless_ai.lib.logger import logger
from pipeless_ai.lib.worker.inference.utils import get_model_path, load_model, parse_input_shape, prepare_frame

class PipelessInferenceSession():
    """
    Create a session of the inference runtime
    """
    def __init__(self, inference_config):
        execution_providers = onnxruntime.get_available_providers()
        force_opset_version = inference_config.get_force_opset_version()
        force_ir_version = inference_config.get_force_ir_version()
        self.input_image_shape_format = inference_config.get_image_shape_format()
        self.force_input_image_width = inference_config.get_image_width()
        self.force_input_image_height = inference_config.get_image_height()
        self.force_input_image_channels = inference_config.get_image_channels()

        if not self.input_image_shape_format:
            logger.warning("worker.inference.image_shape_format not provided for inference model, using default 'height,width,channels")

        model_uri = inference_config.get_model_uri()
        main_model_path = get_model_path(model_uri, "main")
        main_model = load_model(
            main_model_path, "main",
            force_opset_version=force_opset_version, force_ir_version=force_ir_version
        )

        if pre_process_model_uri := inference_config.get_pre_process_model_uri():
            preproc_model_path = get_model_path(pre_process_model_uri, "pre-process")
            preproc_model = load_model(
                preproc_model_path, "pre-process",
                force_opset_version=force_opset_version, force_ir_version=force_ir_version
            )

            try:
                # Merge the models
                prefixed_preproc_model = onnx.compose.add_prefix(preproc_model, "preproc_") # Avoid naming conflicts in the graph
                preproc_output_name = prefixed_preproc_model.graph.output[0].name
                main_input_name = main_model.graph.input[0].name
                io_map = [(preproc_output_name, main_input_name)]

                merged_model = onnx.compose.merge_models(prefixed_preproc_model, main_model, io_map=io_map)
                onnx.save(merged_model, '/tmp/merged.onnx')
                self.session = onnxruntime.InferenceSession('/tmp/merged.onnx', providers=execution_providers)
            except Exception as e:
                logger.error(e)
                sys.exit(1)
        else:
            self.session = onnxruntime.InferenceSession(main_model_path, providers=execution_providers)

        # The ORT will leave only the supported providers and show a warning for the others
        available_ep = self.session.get_providers()
        logger.info(f'Available ORT execution providers: {available_ep}')

        input = self.session.get_inputs()[0]
        input_shape = input.shape
        try:
            force_tuple = (self.force_input_image_width, self.force_input_image_height, self.force_input_image_channels)
            self.input_batch_size, self.input_img_channels, self.input_img_height, self.input_img_width = parse_input_shape(
                input_shape, self.input_image_shape_format, force_tuple)
            logger.info(f"Input images automatically resized to w: {self.input_img_height}, h: {self.input_img_width}. If this is not correct you can force the witdh and height on the configuration.")
        except Exception as e:
            logger.error(f"Error reading the model input shape automatically: {e}. Please provide the input shape via worker.inference.image_width, worker.inference.image_height, worker.inference.image_channels configuration parameters")
            sys.exit(1)

        self.input_name = input.name
        self.input_dtype = input.type
        output =  self.session.get_outputs()[0]
        self.output_name = output.name

        try:
            # Run a first testing inference that usually takes longer than the rest
            test_image = np.zeros((self.input_img_height, self.input_img_width, self.input_img_channels), dtype=np.uint8)
            test_image = prepare_frame(test_image, self.input_dtype, self.input_image_shape_format, self.input_batch_size)
            self.session.run(None, {self.input_name: test_image})
        except Exception as e:
            logger.error(f'There was an error running the testing inference: {e}')
            sys.exit(1)

        logger.info("ORT session ready!")

    def run(self, inference_input_frame):
        try:
            inference_input_frame = prepare_frame(inference_input_frame, self.input_dtype, self.input_image_shape_format, self.input_batch_size, target_height=self.input_img_height, target_width=self.input_img_width)
            input_data = { self.input_name: inference_input_frame }
            # Using IO bindings we signifcantly remove overhead of copying input and outputs
            io_binding = self.session.io_binding()
            # Bind inputs
            for input_name, input_value in input_data.items():
                # Inputs come from CPU after running pre-process. Bind it to wherever the ORT needs it
                io_binding.bind_cpu_input(input_name, input_value)
            # Bind outputs
            output_names = [output.name for output in self.session.get_outputs()]
            for output_name in output_names:
                io_binding.bind_output(output_name)
            # Run inference
            self.session.run_with_iobinding(io_binding)
            io_binding.synchronize_outputs()
            # Get outputs over to CPU (the outputs will be copied from devices (GPU) to the host here)
            outputs = io_binding.copy_outputs_to_cpu()[0]
            return outputs
        except Exception as e:
            logger.error(f'There was an error running inference: {e}')
            return None

def get_inference_session(config):
    """
    Returns an inference session when possible or None
    """
    if config.get_worker().get_inference().get_model_uri():
        inference_config = config.get_worker().get_inference()
        return PipelessInferenceSession(inference_config)
    else:
        return None