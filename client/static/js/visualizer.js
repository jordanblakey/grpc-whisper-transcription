class AudioVisualizer {
    constructor() {
        this.waveCanvas = document.getElementById('waveform');
        this.freqCanvas = document.getElementById('freq-spectrum');
        this.specCanvas = document.getElementById('spectrogram');
        this.waveUiCanvas = document.getElementById('waveform-ui');
        this.freqUiCanvas = document.getElementById('freq-spectrum-ui');
        this.specUiCanvas = document.getElementById('spectrogram-ui');

        this.waveCtx = this.waveCanvas?.getContext('2d');
        this.freqCtx = this.freqCanvas?.getContext('2d');
        this.specCtx = this.specCanvas?.getContext('2d', { willReadFrequently: true });
        this.waveUiCtx = this.waveUiCanvas?.getContext('2d');
        this.freqUiCtx = this.freqUiCanvas?.getContext('2d');
        this.specUiCtx = this.specUiCanvas?.getContext('2d');

        this.analyser = null;
        this.audioContext = null;
        this.animationId = null;
        this.isActive = false;
        
        this.dpr = window.devicePixelRatio || 1;
        this.minFreq = 20;
        this.maxFreq = 20000;
        this.logMin = Math.log10(this.minFreq);
        this.logMax = Math.log10(this.maxFreq);
        this.logRange = this.logMax - this.logMin;

        // Buffers
        this.freqData = null;
        this.timeDataFloat = null;

        window.addEventListener('resize', () => this.resizeCanvas());
        // Initial resize might fail if elements aren't in DOM yet, so call explicitly after load
    }

    start(stream, audioContext) {
        if (this.isActive) return;
        
        console.log('Starting Visualizer...');
        this.audioContext = audioContext;
        this.analyser = this.audioContext.createAnalyser();
        const source = this.audioContext.createMediaStreamSource(stream);
        source.connect(this.analyser);
        
        this.analyser.fftSize = 4096;
        this.analyser.smoothingTimeConstant = 0.6;
        
        this.updateFreqBounds(this.audioContext.sampleRate);
        this.freqData = new Uint8Array(this.analyser.frequencyBinCount);
        this.timeDataFloat = new Float32Array(this.analyser.fftSize);

        this.resizeCanvas();
        this.isActive = true;
        this.draw();
    }

    stop() {
        if (!this.isActive) return;
        console.log('Stopping Visualizer...');
        
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        // We do not close context/stream here as they are managed by Recorder
        this.analyser = null;
        this.isActive = false;
    }

    toggle() {
        // Toggle logic should be handled by orchestrator (Recorder) 
        // because it needs to know whether to start/stop stream or just hide
        // But if stream is running, we can pause rendering?
        // User asked for "Toggle Visualizer" button.
    }

    resizeCanvas() {
        this.dpr = window.devicePixelRatio || 1;
        
        const setSize = (canvas, ctx) => {
            if (!canvas || !ctx) return;
            const rect = canvas.getBoundingClientRect();
            // If hidden or 0 size, skip
            if (rect.width === 0) return;
            
            canvas.width = rect.width * this.dpr;
            canvas.height = rect.height * this.dpr;
            ctx.setTransform(1, 0, 0, 1, 0, 0); 
            ctx.scale(this.dpr, this.dpr);
        };

        setSize(this.waveCanvas, this.waveCtx);
        setSize(this.freqCanvas, this.freqCtx);
        setSize(this.specCanvas, this.specCtx);
        setSize(this.waveUiCanvas, this.waveUiCtx);
        setSize(this.freqUiCanvas, this.freqUiCtx);
        setSize(this.specUiCanvas, this.specUiCtx);
    }

    updateFreqBounds(sampleRate) {
        this.maxFreq = 20000; 
        this.logMax = Math.log10(this.maxFreq);
        this.logRange = this.logMax - this.logMin;
    }

    getFreqData(freq, sampleRate, dataArray) {
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

    getColor(value) {
        const p = value / 255;
        if (p < 0.1) return `rgb(0,0,${Math.floor(p*10*255)})`;
        if (p < 0.3) return `rgb(0,${Math.floor((p-0.1)*5*255)},255)`;
        if (p < 0.6) return `rgb(0,255,${Math.floor((0.6-p)*3.33*255)})`;
        return `rgb(255,${Math.floor((1-p)*2.5*255)},0)`;
    }

    draw() {
        if (!this.isActive) return;
        this.animationId = requestAnimationFrame(() => this.draw());

        if (!this.analyser) return;

        this.analyser.getByteFrequencyData(this.freqData);
        this.analyser.getFloatTimeDomainData(this.timeDataFloat);

        const sampleRate = this.audioContext.sampleRate;
        const bufferLength = this.analyser.frequencyBinCount;
        const timeBufferLength = this.analyser.fftSize;

        this.renderWaveformFrame(this.timeDataFloat, timeBufferLength);
        this.renderSpectrumFrame(this.freqData, sampleRate);
        this.renderSpectrogramFrame(this.freqData, sampleRate);
        
        this.drawFrequencyLabels(this.freqUiCtx, this.freqUiCanvas, sampleRate);
        this.drawFrequencyLabels(this.specUiCtx, this.specUiCanvas, sampleRate);
        
        this.drawYAxisLabels(this.waveUiCtx, this.waveUiCanvas, 'amp');
        this.drawYAxisLabels(this.freqUiCtx, this.freqUiCanvas, 'db');
    }

    renderWaveformFrame(timeData, bufferLength) {
        if (!this.waveCanvas) return;
        const h = this.waveCanvas.height / this.dpr;
        const w = this.waveCanvas.width / this.dpr;
        
        this.waveCtx.fillStyle = '#000';
        this.waveCtx.fillRect(0, 0, w, h);
        this.waveCtx.lineWidth = 1.5;
        this.waveCtx.strokeStyle = '#00ff00'; 
        this.waveCtx.beginPath();

        const plotLength = 1000;
        let offset = 0;
        let mean = 0;

        const maxSearchWindow = 1600; 
        const searchStart = Math.max(0, bufferLength - plotLength - maxSearchWindow);
        const searchEnd = bufferLength - plotLength;
        
        let sum = 0;
        for (let i = searchStart; i < bufferLength; i++) sum += timeData[i];
        mean = sum / (bufferLength - searchStart);
        
        offset = searchEnd; 
        for (let i = searchEnd; i >= searchStart; i--) {
            if (timeData[i] < mean && timeData[i+1] >= mean) {
                offset = i;
                break; 
            }
        }
        
        let peak = 0;
        for (let i = 0; i < plotLength; i++) {
            const amp = Math.abs(timeData[offset + i] - mean);
            if (amp > peak) peak = amp;
        }

        const targetPeak = 0.8;
        const maxGain = 20.0; 
        const gain = Math.min(maxGain, targetPeak / (peak || 0.01));

        const sliceWidth = w * 1.0 / plotLength;
        let x = 0;
        this.waveCtx.beginPath();
        for (let i = 0; i < plotLength; i++) {
            const idx = offset + i;
            const v = (timeData[idx] - mean) * gain; 
            const y = (h / 2) + (v * (h / 2)); 
            
            if (idx === offset) this.waveCtx.moveTo(x, y);
            else this.waveCtx.lineTo(x, y);
            
            x += sliceWidth;
        }
        this.waveCtx.stroke();
    }

    renderSpectrumFrame(freqData, sampleRate) {
        if (!this.freqCanvas) return;
        const h = this.freqCanvas.height / this.dpr;
        const w = this.freqCanvas.width / this.dpr;

        this.freqCtx.fillStyle = '#000';
        this.freqCtx.fillRect(0, 0, w, h);

        for (let x = 0; x < w; x++) {
            const logFreq = this.logMin + (x / w) * this.logRange;
            const freq = Math.pow(10, logFreq);
            const value = this.getFreqData(freq, sampleRate, freqData);
            const barHeight = (value / 255) * h;
            
            this.freqCtx.fillStyle = `hsl(${x / w * 300}, 100%, 50%)`;
            this.freqCtx.fillRect(x, h - barHeight, 1, barHeight);
        }
    }

    renderSpectrogramFrame(freqData, sampleRate) {
        if (!this.specCanvas) return;
        const h = this.specCanvas.height / this.dpr;
        const w = this.specCanvas.width / this.dpr;

        this.specCtx.drawImage(this.specCanvas, 
            0, 0, this.specCanvas.width, this.specCanvas.height - 1 * this.dpr, 
            0, 1, w, h - 1
        );

         for (let x = 0; x < w; x++) {
            const logFreq = this.logMin + (x / w) * this.logRange;
            const freq = Math.pow(10, logFreq);
            const value = this.getFreqData(freq, sampleRate, freqData);
            
            this.specCtx.fillStyle = this.getColor(value);
            this.specCtx.fillRect(x, 0, 1, 1);
        }
    }

    drawFrequencyLabels(ctx, canvas, sampleRate) {
        if (!ctx || !canvas) return;
        const h = canvas.height / this.dpr;
        const w = canvas.width / this.dpr;

        ctx.clearRect(0, 0, w, h);
        ctx.fillStyle = '#fff';
        const fontSize = 10;
        ctx.font = `bold ${fontSize}px sans-serif`;
        ctx.textAlign = 'left';
        ctx.fillText('20Hz', 4, h - 4);
        ctx.textAlign = 'center';
        const x1k = (Math.log10(1000) - this.logMin) / this.logRange * w;
        if (x1k > 0 && x1k < w) {
            ctx.fillText('1kHz', x1k, h - 4);
        }
        ctx.textAlign = 'right';
        ctx.fillText('20kHz', w - 4, h - 4);
    }

    drawYAxisLabels(ctx, canvas, type) {
        if (!ctx || !canvas) return;
        const h = canvas.height / this.dpr;
        const w = canvas.width / this.dpr;
        
        ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
        ctx.font = '9px sans-serif';
        ctx.textAlign = 'right';

        if (type === 'amp') {
            ctx.fillText('1.0', w - 4, 10);
            ctx.fillText('0.0', w - 4, h/2 + 4);
            ctx.fillText('-1.0', w - 4, h - 4);
        } else if (type === 'db') {
            const max = (this.analyser) ? this.analyser.maxDecibels : -30;
            const min = (this.analyser) ? this.analyser.minDecibels : -100;
            
            ctx.fillText(`${max}dB`, w - 4, 10);
            ctx.fillText(`${Math.round((max+min)/2)}dB`, w - 4, h/2 + 4);
            ctx.fillText(`${min}dB`, w - 4, h - 4);
        }
    }
}
