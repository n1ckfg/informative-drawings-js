with open("index.html") as f:
    html = f.read()

# 1. Update ort.js to ort.min.js
html = html.replace('<script src="./js/libraries/ort/ort.js"></script>', '<script src="./js/libraries/ort/ort.min.js"></script>')

# 2. Replace controls with dropdown
old_controls = """    <div class="controls">
      <div>
        Resolution:
        <input type="number" id="widthEl" value="320" min="16" step="1"> x
        <input type="number" id="heightEl" value="240" min="16" step="1">
      </div>
      <div>
        <button id="startBtn" onclick="toggle()" disabled>loading model...</button>
        <span id="stats">FPS: -- | inference: -- ms</span>
      </div>
      <div id="statusEl"></div>
    </div>"""

new_controls = """    <div class="controls">
      <div>
        Backend:
        <select id="backendEl">
          <option value="auto">auto (WebGPU if available)</option>
          <option value="webgpu">WebGPU</option>
          <option value="wasm">WASM (CPU)</option>
        </select>
        <span id="backendInfo"></span>
      </div>
      <div>
        Resolution:
        <select id="resEl">
          <option value="320x240">320 x 240</option>
          <option value="640x480">640 x 480</option>
          <option value="dynamic">Custom (Dynamic shape)</option>
        </select>
        <span id="customRes" style="display:none">
          <input type="number" id="widthEl" value="320" min="16" step="1"> x
          <input type="number" id="heightEl" value="240" min="16" step="1">
        </span>
      </div>
      <div>
        <button id="startBtn" onclick="toggle()" disabled>loading model...</button>
        <span id="stats">FPS: -- | inference: -- ms</span>
      </div>
      <div id="statusEl"></div>
    </div>"""

html = html.replace(old_controls, new_controls)

# 3. Replace the ort init code
old_js = """      if(self.crossOriginIsolated) { // needs to be cross-origin-isolated to use wasm threads. you need to serve this html file with these two headers: https://web.dev/coop-coep/
        ort.env.wasm.numThreads = navigator.hardwareConcurrency
      }
      ort.env.wasm.proxy = true;
      ort.env.wasm.wasmPaths = new URL('./js/libraries/ort/', location.href).href; // must be absolute: the proxy worker runs from a blob: URL, so relative paths can't resolve

      if(!window.OffscreenCanvas) alert("Your browser doesn't support OffscreenCanvas - a browser feature that was standardized way back in 2018. Please use a modern browser like Chrome, Edge or Brave.");

      // Canvas used to scale/crop webcam frames down to the model input resolution
      const inputCanvas = new OffscreenCanvas(320, 240);
      const inputCtx = inputCanvas.getContext("2d", { willReadFrequently: true });
      const outputCtx = outputCanvas.getContext("2d");

      let onnxSession;
      let running = false;
      let stream = null;

      (async function() {
        //const url="https://huggingface.co/rocca/informative-drawings-line-art-onnx/resolve/main/model.onnx";
        const url="model.onnx";

        console.log("Downloading model... (see network tab for progress)");
        onnxSession = await ort.InferenceSession.create(url, { executionProviders: ["wasm"] });
        console.log("Model loaded.");
        startBtn.disabled = false;
        startBtn.textContent = "start webcam";
      })();

      function getResolution() {
        const w = Math.max(16, Math.round(Number(widthEl.value)) || 320);
        const h = Math.max(16, Math.round(Number(heightEl.value)) || 240);
        return { width: w, height: h };
      }"""

new_js = """      if(self.crossOriginIsolated) { // needs to be cross-origin-isolated to use wasm threads. you need to serve this html file with these two headers: https://web.dev/coop-coep/
        ort.env.wasm.numThreads = navigator.hardwareConcurrency
      }
      ort.env.wasm.wasmPaths = new URL('./js/libraries/ort/', location.href).href; // must be absolute: the proxy worker runs from a blob: URL, so relative paths can't resolve

      if(!window.OffscreenCanvas) alert("Your browser doesn't support OffscreenCanvas - a browser feature that was standardized way back in 2018. Please use a modern browser like Chrome, Edge or Brave.");

      // Canvas used to scale/crop webcam frames down to the model input resolution
      const inputCanvas = new OffscreenCanvas(320, 240);
      const inputCtx = inputCanvas.getContext("2d", { willReadFrequently: true });
      const outputCtx = outputCanvas.getContext("2d");

      let onnxSession;
      let activeBackend = null;
      let running = false;
      let stream = null;

      // Backend and fixed resolution are chosen once per page load.
      const urlParams = new URLSearchParams(location.search);
      const requestedBackend = ["auto", "webgpu", "wasm"].includes(urlParams.get("backend")) ? urlParams.get("backend") : "auto";
      backendEl.value = requestedBackend;
      backendEl.onchange = () => {
        urlParams.set("backend", backendEl.value);
        location.search = urlParams.toString();
      };

      const requestedRes = ["320x240", "640x480", "dynamic"].includes(urlParams.get("res")) ? urlParams.get("res") : "320x240";
      resEl.value = requestedRes;
      if (requestedRes === "dynamic") customRes.style.display = "inline";
      resEl.onchange = () => {
        urlParams.set("res", resEl.value);
        location.search = urlParams.toString();
      };

      function getResolution() {
        if (resEl.value === "dynamic") {
          const w = Math.max(16, Math.round(Number(widthEl.value)) || 320);
          const h = Math.max(16, Math.round(Number(heightEl.value)) || 240);
          return { width: w, height: h };
        } else {
          const [w, h] = resEl.value.split("x").map(Number);
          return { width: w, height: h };
        }
      }

      async function isWebGPUAvailable() {
        if(!navigator.gpu) return false;
        try { return !!(await navigator.gpu.requestAdapter()); } catch(e) { return false; }
      }

      async function createSession(url, backend) {
        // The proxy worker only supports the wasm EP; WebGPU must run on the main thread.
        ort.env.wasm.proxy = backend === "wasm";
        return ort.InferenceSession.create(url, { executionProviders: [backend] });
      }

      (async function() {
        let backend = requestedBackend;
        if(backend !== "wasm" && !(await isWebGPUAvailable())) {
          if(backend === "webgpu") statusEl.textContent = "WebGPU is not available in this browser - falling back to WASM.";
          backend = "wasm";
        }

        let url = "models/model.onnx";
        if (requestedRes !== "dynamic") {
          url = `models/model_${requestedRes}${backend === "webgpu" ? "_fp16" : ""}.onnx`;
        }

        console.log(`Downloading model ${url}... (see network tab for progress) [backend: ${backend}]`);
        try {
          onnxSession = await createSession(url, backend);
        } catch(e) {
          if(backend !== "webgpu") throw e;
          console.warn("WebGPU session creation failed, falling back to WASM:", e);
          statusEl.textContent = "WebGPU failed to initialize - falling back to WASM: " + (e.message || e);
          backend = "wasm";
          
          if (requestedRes !== "dynamic") {
             url = `models/model_${requestedRes}.onnx`; // Fallback to fp32 model if we fall back to wasm
          }
          onnxSession = await createSession(url, backend);
        }
        activeBackend = backend;
        backendInfo.textContent = backend === "webgpu"
          ? "active: WebGPU"
          : `active: WASM (${ort.env.wasm.numThreads || 1} threads${self.crossOriginIsolated ? "" : ", not cross-origin isolated"}${ort.env.wasm.proxy ? ", proxy worker" : ""})`;
        console.log(`Model loaded (ORT ${ort.env.versions?.web ?? "?"}, backend: ${backend}).`);

        // Warm up at the default resolution so shader compilation / first-run allocation isn't counted in FPS.
        startBtn.textContent = "warming up...";
        const { width, height } = getResolution();
        const r = await benchmark(width, height, 3);
        console.log(`Warmup ${width}x${height}: first run ${r.first.toFixed(0)}ms, then avg ${r.avg.toFixed(1)}ms`);

        startBtn.disabled = false;
        startBtn.textContent = "start webcam";
      })().catch(e => {
        console.error(e);
        statusEl.textContent = "Failed to load model: " + (e.message || e);
        startBtn.textContent = "model failed to load";
      });

      // Times inference on synthetic input (no webcam needed). Also callable from the console,
      // e.g. `await benchmark(320, 240, 20)`, to compare backends/resolutions.
      async function benchmark(width, height, iterations = 20) {
        const times = [];
        for(let i = 0; i < iterations; i++) {
          const data = new Float32Array(3 * width * height).fill(0.5);
          const t = performance.now();
          await onnxSession.run({ 'input': new ort.Tensor('float32', data, [1, 3, height, width]) });
          times.push(performance.now() - t);
        }
        const rest = times.length > 1 ? times.slice(1) : times;
        const avg = rest.reduce((a, b) => a + b, 0) / rest.length;
        return { backend: activeBackend, width, height, first: times[0], avg, fps: 1000 / avg };
      }"""

html = html.replace(old_js, new_js)

with open("index.html", "w") as f:
    f.write(html)
