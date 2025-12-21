const audioToggleBtn = document.getElementById('audio-toggle');
const visualizerToggleBtn = document.getElementById('visualizer-toggle');
const waveCanvas = document.getElementById('waveform');
const freqCanvas = document.getElementById('freq-spectrum');
const specCanvas = document.getElementById('spectrogram');
const waveUiCanvas = document.getElementById('waveform-ui');
const freqUiCanvas = document.getElementById('freq-spectrum-ui');
const specUiCanvas = document.getElementById('spectrogram-ui');

const waveCtx = waveCanvas.getContext('2d');
const freqCtx = freqCanvas.getContext('2d');
const specCtx = specCanvas.getContext('2d', { willReadFrequently: true });
const waveUiCtx = waveUiCanvas.getContext('2d');
const freqUiCtx = freqUiCanvas.getContext('2d');
const specUiCtx = specUiCanvas.getContext('2d');

let audioContext;
let analyser;
let microphone;
let animationId;
let isStreaming = false;
let isVisualizerOnly = false;
let socket;
const transcriptionDiv = document.getElementById('transcription');

// Pre-allocate buffers to avoid Garbage Collection inside drawVisualizer
let freqData;
let timeDataFloat;

let dpr = window.devicePixelRatio || 1;
let logicalWidth, logicalHeight;

function resizeCanvas() {
    dpr = window.devicePixelRatio || 1;
    
    function setSize(canvas, ctx) {
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        
        ctx.setTransform(1, 0, 0, 1, 0, 0); 
        ctx.scale(dpr, dpr);
    }

    setSize(waveCanvas, waveCtx);
    setSize(freqCanvas, freqCtx);
    setSize(specCanvas, specCtx);
    setSize(waveUiCanvas, waveUiCtx);
    setSize(freqUiCanvas, freqUiCtx);
    setSize(specUiCanvas, specUiCtx);

    logicalWidth = waveCanvas.width / dpr;
}

// Initial resize handled later

let minFreq = 20;
let maxFreq = 20000;
let logMin = Math.log10(minFreq);
let logMax = Math.log10(maxFreq);
let logRange = logMax - logMin;

function updateFreqBounds(sampleRate) {
    maxFreq = 20000; // Keep fixed visual range to avoid "stretching" UI look
    logMax = Math.log10(maxFreq);
    logRange = logMax - logMin;
    console.log(`Visual range fixed: 20Hz - ${maxFreq}Hz (Sample rate: ${sampleRate}Hz)`);
}

window.addEventListener('resize', resizeCanvas);
resizeCanvas();

function getFreqData(freq, sampleRate, dataArray) {
    // Revert to Linear Interpolation (Real Data representation)
    const nyquist = sampleRate / 2;
    const index = freq * (dataArray.length) / nyquist;
    const i1 = Math.floor(index);
    const i2 = i1 + 1;
    
    if (i1 >= dataArray.length) return 0;
    
    const v1 = dataArray[i1];
    const v2 = (i2 < dataArray.length) ? dataArray[i2] : v1;
    
    const t = index - i1;
    return v1 * (1 - t) + v2 * t;
}

function getColor(value) {
    const p = value / 255;
    if (p < 0.1) return `rgb(0,0,${Math.floor(p*10*255)})`;
    if (p < 0.3) return `rgb(0,${Math.floor((p-0.1)*5*255)},255)`;
    if (p < 0.6) return `rgb(0,255,${Math.floor((0.6-p)*3.33*255)})`;
    return `rgb(255,${Math.floor((1-p)*2.5*255)},0)`;
}

function renderWaveformFrame(waveCtx, timeData, bufferLength) {
    const h = waveCanvas.height / dpr;
    const w = waveCanvas.width / dpr;
    
    waveCtx.fillStyle = '#000';
    waveCtx.fillRect(0, 0, w, h);
    waveCtx.lineWidth = 1.5;
    waveCtx.strokeStyle = '#00ff00'; 
    waveCtx.beginPath();

    const plotLength = 1000;
    let offset = 0;
    let mean = 0;

    // --- Optimized Oscilloscope Triggering ---
    // Search backwards from the END of the buffer for lower latency
    // Only search the last ~1600 samples (100ms at 16kHz) for the trigger
    const maxSearchWindow = 1600; // ~100ms search window
    const searchStart = Math.max(0, bufferLength - plotLength - maxSearchWindow);
    const searchEnd = bufferLength - plotLength;
    
    // Calculate mean only from the recent window for faster computation
    let sum = 0;
    for (let i = searchStart; i < bufferLength; i++) sum += timeData[i];
    mean = sum / (bufferLength - searchStart);
    
    // Search backwards from most recent data
    offset = searchEnd; // Default to end if no trigger found
    for (let i = searchEnd; i >= searchStart; i--) {
        // Find transition across the mean (rising edge)
        if (timeData[i] < mean && timeData[i+1] >= mean) {
            offset = i;
            break; // Take the FIRST (most recent) trigger we find
        }
    }
    
    // Calculate peak amplitude in this window for auto-scaling
    let peak = 0;
    for (let i = 0; i < plotLength; i++) {
        const amp = Math.abs(timeData[offset + i] - mean);
        if (amp > peak) peak = amp;
    }

    // Auto-scale: We want peak to reach ~80% of h/2 (0.4 of h)
    // but we cap the gain so we don't amplify noise floor too much
    const targetPeak = 0.8;
    const maxGain = 20.0; // Don't scale up more than 20x
    const gain = Math.min(maxGain, targetPeak / (peak || 0.01));

    const sliceWidth = w * 1.0 / plotLength;
    let x = 0;
    waveCtx.beginPath();
    for (let i = 0; i < plotLength; i++) {
        const idx = offset + i;
        const v = (timeData[idx] - mean) * gain; 
        const y = (h / 2) + (v * (h / 2)); 
        
        if (idx === offset) waveCtx.moveTo(x, y);
        else waveCtx.lineTo(x, y);
        
        x += sliceWidth;
    }
    waveCtx.stroke();
}

function renderSpectrumFrame(freqCtx, freqData, audioContext,logMin,logMax,logRange,sampleRate) {
    const h = freqCanvas.height / dpr;
    const w = freqCanvas.width / dpr;

    freqCtx.fillStyle = '#000';
    freqCtx.fillRect(0, 0, w, h);

    for (let x = 0; x < w; x++) {
        const logFreq = logMin + (x / w) * logRange;
        const freq = Math.pow(10, logFreq);
        const value = getFreqData(freq, sampleRate, freqData);
        const barHeight = (value / 255) * h;
        
        freqCtx.fillStyle = `hsl(${x / w * 300}, 100%, 50%)`;
        freqCtx.fillRect(x, h - barHeight, 1, barHeight);
    }
}

function drawFrequencyLabels(ctx, canvas, logMin, logMax, logRange, sampleRate) {
    const h = canvas.height / dpr;
    const w = canvas.width / dpr;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#fff';
    const fontSize = 10;
    ctx.font = `bold ${fontSize}px sans-serif`;
    ctx.textAlign = 'left';
    ctx.fillText('20Hz', 4, h - 4);
    ctx.textAlign = 'center';
    const x1k = (Math.log10(1000) - logMin) / logRange * w;
    if (x1k > 0 && x1k < w) {
        ctx.fillText('1kHz', x1k, h - 4);
    }
    ctx.textAlign = 'right';
    ctx.fillText('20kHz', w - 4, h - 4);
}

function renderSpectrogramFrame(specCtx,freqData,logMin,logMax,logRange,sampleRate) {
    const h = specCanvas.height / dpr;
    const w = specCanvas.width / dpr;

    // Draw previous image shifted down by 1 logical pixel
    specCtx.drawImage(specCanvas, 
        0, 0, specCanvas.width, specCanvas.height - 1 * dpr, 
        0, 1, w, h - 1
    );

     for (let x = 0; x < w; x++) {
        const logFreq = logMin + (x / w) * logRange;
        const freq = Math.pow(10, logFreq);
        const value = getFreqData(freq, sampleRate, freqData);
        
        specCtx.fillStyle = getColor(value);
        specCtx.fillRect(x, 0, 1, 1);
    }
}

function drawVisualizer() {
    if (!isStreaming && !isVisualizerOnly) return;

    animationId = requestAnimationFrame(drawVisualizer);

    const bufferLength = analyser.frequencyBinCount;
    const timeBufferLength = analyser.fftSize;
    
    // Use pre-allocated buffers
    analyser.getByteFrequencyData(freqData);
    analyser.getFloatTimeDomainData(timeDataFloat);

    const sampleRate = audioContext.sampleRate;
    const logMin = Math.log10(minFreq);
    const logMax = Math.log10(maxFreq);
    const logRange = logMax - logMin;

    renderWaveformFrame(waveCtx, timeDataFloat, timeBufferLength);
    renderSpectrumFrame(freqCtx, freqData, audioContext, logMin, logMax, logRange, sampleRate);
    renderSpectrogramFrame(specCtx,freqData, logMin, logMax, logRange, sampleRate);
    
    // Draw labels on overlay canvases
    drawFrequencyLabels(freqUiCtx, freqUiCanvas, logMin, logMax, logRange, sampleRate);
    drawFrequencyLabels(specUiCtx, specUiCanvas, logMin, logMax, logRange, sampleRate);
    
    // Draw Y-axis labels (dB for spectrum, Amp for wave)
    drawYAxisLabels(waveUiCtx, waveUiCanvas, 'amp');
    drawYAxisLabels(freqUiCtx, freqUiCanvas, 'db');
}

function drawYAxisLabels(ctx, canvas, type) {
    const h = canvas.height / dpr;
    const w = canvas.width / dpr;
    
    // Small, semi-transparent labels
    ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'right';

    if (type === 'amp') {
        ctx.fillText('1.0', w - 4, 10);
        ctx.fillText('0.0', w - 4, h/2 + 4);
        ctx.fillText('-1.0', w - 4, h - 4);
    } else if (type === 'db') {
        // Based on default minDecibels (-100) and maxDecibels (-30)
        // If we haven't set them, we assume defaults
        const max = (analyser) ? analyser.maxDecibels : -30;
        const min = (analyser) ? analyser.minDecibels : -100;
        
        ctx.fillText(`${max}dB`, w - 4, 10);
        ctx.fillText(`${Math.round((max+min)/2)}dB`, w - 4, h/2 + 4);
        ctx.fillText(`${min}dB`, w - 4, h - 4);
    }
}

async function startStream() {
    try {
        const historyDiv = document.getElementById('transcript-history');
        const partialDiv = document.getElementById('partial-result');
        if (historyDiv) historyDiv.innerHTML = '';
        if (partialDiv) partialDiv.textContent = '';
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                noiseSuppression: false,
                echoCancellation: false,
                autoGainControl: false
            } 
        });
        
        audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
        console.log(`AudioContext initialized at ${audioContext.sampleRate}Hz`);

        analyser = audioContext.createAnalyser();
        microphone = audioContext.createMediaStreamSource(stream);
        
        microphone.connect(analyser);
        analyser.fftSize = 4096; // Better resolution for low end at 16kHz
        analyser.smoothingTimeConstant = 0.6; // Slightly more smoothing for visual stability
        
        updateFreqBounds(audioContext.sampleRate);

        // Initialize WebSocket
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        socket = new WebSocket(`${protocol}//${window.location.host}/ws/audio`);
        
        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            const historyDiv = document.getElementById('transcript-history');
            const partialDiv = document.getElementById('partial-result');

            if (data.is_final) {
                // Remove the partial text when a final arrives (it might be the same content)
                partialDiv.textContent = '';

                const segment = document.createElement('div');
                segment.className = 'transcript-segment';
                
                const seconds = Math.floor(data.start_time);
                const mm = String(Math.floor(seconds / 60)).padStart(2, '0');
                const ss = String(seconds % 60).padStart(2, '0');
                const timestamp = `[${mm}:${ss}]`;
                
                segment.innerHTML = `<span class="timestamp">${timestamp}</span>${data.text}`;
                historyDiv.appendChild(segment);
            } else {
                // Update the ephemeral partial area
                partialDiv.textContent = data.text;
            }

            // Keep the scroll at the bottom
            transcriptionDiv.scrollTop = transcriptionDiv.scrollHeight;
        };

        socket.onopen = () => {
            console.log('WebSocket connected');
            // Send initial configuration
            socket.send(JSON.stringify({ sample_rate: audioContext.sampleRate }));
        };

        socket.onclose = () => {
            console.log('WebSocket disconnected');
        };

        // Load AudioWorklet processor
        await audioContext.audioWorklet.addModule('/static/js/audio-processor.js');
        const processor = new AudioWorkletNode(audioContext, 'audio-processor');
        
        microphone.connect(processor);
        processor.connect(audioContext.destination);

        processor.port.onmessage = (event) => {
            if (socket && socket.readyState === WebSocket.OPEN) {
                const inputData = event.data; // This is the Float32Array from the worklet
                socket.send(inputData.buffer);
            }
        };

        // Initialize buffers after analyser is configured
        freqData = new Uint8Array(analyser.frequencyBinCount);
        timeDataFloat = new Float32Array(analyser.fftSize); 

        isStreaming = true;
        audioToggleBtn.textContent = 'Stop Streaming';
        audioToggleBtn.classList.add('active');
        
        drawVisualizer();

        audioToggleBtn.stream = stream;
        audioToggleBtn.processor = processor;

    } catch (err) {
        console.error('Error accessing microphone:', err);
        alert('Error accessing microphone. Please ensure you have granted permission.');
    }
}

function stopStream() {
    if (audioToggleBtn.stream) {
        audioToggleBtn.stream.getTracks().forEach(track => track.stop());
        audioToggleBtn.stream = null;
    }

    if (audioToggleBtn.processor) {
        audioToggleBtn.processor.disconnect();
        audioToggleBtn.processor = null;
    }
    
    if (socket) {
        socket.close();
        socket = null;
    }
    
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }

    if (animationId) {
        cancelAnimationFrame(animationId);
    }

    isStreaming = false;
    audioToggleBtn.textContent = 'Start Streaming';
    audioToggleBtn.classList.remove('active');
}

audioToggleBtn.addEventListener('click', () => {
    if (!isStreaming) {
        // Stop visualizer-only mode if active
        if (isVisualizerOnly) {
            stopVisualizerOnly();
        }
        startStream();
    } else {
        stopStream();
    }
});

async function startVisualizerOnly() {
    try {
        console.log('Starting visualizer-only mode...');
        
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                noiseSuppression: false,
                echoCancellation: false,
                autoGainControl: false
            } 
        });
        
        console.log('Microphone access granted');
        
        audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
        console.log(`AudioContext (Visualizer-only) initialized at ${audioContext.sampleRate}Hz`);
        analyser = audioContext.createAnalyser();
        microphone = audioContext.createMediaStreamSource(stream);
        
        microphone.connect(analyser);
        analyser.fftSize = 4096; 
        analyser.smoothingTimeConstant = 0.6;

        updateFreqBounds(audioContext.sampleRate);

        // No WebSocket connection - just visualizer
        const bufferLength = analyser.frequencyBinCount;
        freqData = new Uint8Array(bufferLength);
        timeDataFloat = new Float32Array(analyser.fftSize);

        isVisualizerOnly = true;
        visualizerToggleBtn.textContent = 'Stop Visualizer';
        visualizerToggleBtn.classList.add('active');
        
        console.log('Starting visualizer animation...');
        drawVisualizer();

        visualizerToggleBtn.stream = stream;
        
        console.log('Visualizer-only mode started successfully');

    } catch (err) {
        console.error('Error accessing microphone:', err);
        alert('Error accessing microphone. Please ensure you have granted permission.');
    }
}

function stopVisualizerOnly() {
    console.log('Stopping visualizer-only mode...');
    
    if (visualizerToggleBtn.stream) {
        visualizerToggleBtn.stream.getTracks().forEach(track => track.stop());
        visualizerToggleBtn.stream = null;
    }
    
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }

    if (animationId) {
        cancelAnimationFrame(animationId);
    }

    isVisualizerOnly = false;
    visualizerToggleBtn.textContent = 'Visualizer Only';
    visualizerToggleBtn.classList.remove('active');
    
    console.log('Visualizer-only mode stopped');
}

visualizerToggleBtn.addEventListener('click', () => {
    console.log('Visualizer button clicked. Current state:', { isVisualizerOnly, isStreaming });
    
    if (!isVisualizerOnly) {
        // Stop streaming mode if active
        if (isStreaming) {
            stopStream();
        }
        startVisualizerOnly();
    } else {
        stopVisualizerOnly();
    }
});
