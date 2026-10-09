Why this version isn’t fast

It loads onnxruntime-web 1.10.0 with only the wasm execution provider, enables threads only when the page is cross-origin isolated, and runs in proxy mode. Its preprocessing also builds nested JS arrays pixel by pixel and then calls .flat().flat(), which is likely as slow as the inference. And even though a comment says it resizes to 256px width, it actually feeds the image at its native resolution. 
githubusercontent

What a fast rebuild would involve

Re-export from Chan’s checkpoints at a fixed input size (512² or 768², say), run onnxsim on it, and make an fp16 variant. The generator is a small ResNet-style conv net with no exotic ops, so it should map cleanly onto GPU kernels.
Use current onnxruntime-web with the webgpu execution provider, falling back to wasm with SIMD and threads. Serve with COOP/COEP headers so threads are actually enabled.
Do the pre- and post-processing on the GPU: upload a VideoFrame or ImageBitmap, normalize in a compute shader, and keep the output tensor on the GPU with preferredOutputLocation: 'gpu-buffer' so you can draw it straight to a WebGPU canvas without reading it back. That’s what makes live video rates realistic.
Bundle all three styles (anime, contour, opensketch) as separate sessions, or as one graph with a style switch.

If you want to use this in the live performance pipeline, step 3 is the one that matters most, since it lets frames go from camera to model to canvas without ever touching JS arrays. I can put together a WebGPU/WASM build with a benchmark page if that would help.