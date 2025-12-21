class WaveformDisplay {
    constructor(canvas, dpr = window.devicePixelRatio || 1) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.dpr = dpr;
        
        // Configuration
        this.strokeStyle = '#00ff00';
        this.fillStyle = '#000000';
        this.lineWidth = 1.5;
        this.plotLength = 1000; // Number of points to plot for live view
        this.maxGain = 1.0;     // No gain needed for normalized history
        
        // State
        this.analyser = null;
        this.peaks = []; // Store live peaks
        this.staticBuffer = null; // AudioBuffer for static display
        this.audioElement = null; // Associated audio element for playhead
        this.isLive = false;
        this.animationId = null;

        this.resize();
        window.addEventListener('resize', () => this.resize());
    }

    resize() {
        const rect = this.canvas.getBoundingClientRect();
        this.canvas.width = rect.width * this.dpr;
        this.canvas.height = rect.height * this.dpr;
        this.ctx.setTransform(1, 0, 0, 1, 0, 0); 
        this.ctx.scale(this.dpr, this.dpr);
        this.width = this.canvas.width / this.dpr;
        this.height = this.canvas.height / this.dpr;
        
        // Redraw if we have static content
        if (!this.isLive && this.staticBuffer) {
            this.drawStatic();
        }
    }

    connect(analyser) {
        this.analyser = analyser;
        this.timeData = new Uint8Array(analyser.fftSize); // Use Uint8 for byte data as per recorder.html
        this.isLive = true;
        this.staticBuffer = null;
        this.peaks = [];
        this.startLoop();
    }

    load(audioBuffer) {
        this.stopLoop();
        this.isLive = false;
        this.analyser = null;
        this.staticBuffer = audioBuffer;
        this.audioElement = null; // Clear old audio element to prevent stale playhead
        this.drawStatic();
    }

    bindAudio(audioElement) {
        this.audioElement = audioElement;
        
        // Immediate redraw to show playhead at current time (usually 0)
        if (!this.isLive && this.staticBuffer) {
           this.drawStatic();
        }

        // Re-draw on timeupdate to move playhead
        this.audioElement.addEventListener('timeupdate', () => {
            if (!this.isLive && this.staticBuffer) {
                this.drawStatic();
            }
        });
        
        // Also animation loop for smoother playhead? 
        // For now, timeupdate might be enough, or we requestAnimationFrame during play
        this.audioElement.addEventListener('play', () => {
             if (!this.isLive && this.staticBuffer) {
                 this.startPlayheadLoop();
             }
        });
        this.audioElement.addEventListener('pause', () => this.stopLoop());
        this.audioElement.addEventListener('ended', () => this.drawStatic());
    }

    startLoop() {
        if (this.animationId) cancelAnimationFrame(this.animationId);
        const loop = () => {
            if (this.isLive) {
                this.drawLive();
                this.animationId = requestAnimationFrame(loop);
            }
        };
        loop();
    }
    
    startPlayheadLoop() {
        if (this.animationId) cancelAnimationFrame(this.animationId);
        const loop = () => {
            if (!this.audioElement.paused && !this.isLive) {
                this.drawStatic();
                this.animationId = requestAnimationFrame(loop);
            }
        };
        loop();
    }

    stopLoop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }

    drawLive() {
        if (!this.analyser) return;
        this.analyser.getByteTimeDomainData(this.timeData);
        
        // Calculate max peak for this frame
        let max = 0;
        for(let i = 0; i < this.timeData.length; i++) {
            const v = Math.abs(this.timeData[i] - 128) / 128; // Normalize 0-1
            if (v > max) max = v;
        }
        this.peaks.push(max);

        // Clear background
        this.ctx.fillStyle = this.fillStyle;
        this.ctx.fillRect(0, 0, this.width, this.height);
        
        this.ctx.fillStyle = '#0f0'; // Bright green as requested (matching recorder.html style)

        const totalPeaks = this.peaks.length;
        if (totalPeaks === 0) return;

        if (totalPeaks <= this.width) {
            const barWidth = this.width / totalPeaks;
            this.ctx.beginPath();
            for (let i = 0; i < totalPeaks; i++) {
                const x = i * barWidth;
                const amp = this.peaks[i];
                const barHeight = amp * this.height;
                const y = (this.height - barHeight) / 2;
                this.ctx.fillRect(x, y, Math.max(1, barWidth - 0.5), barHeight); 
            }
        } else {
            // Downsample mode
            const samplesPerPixel = totalPeaks / this.width;
            this.ctx.beginPath();
            for (let x = 0; x < this.width; x++) {
                const startIdx = Math.floor(x * samplesPerPixel);
                const endIdx = Math.floor((x + 1) * samplesPerPixel);
                
                let maxAmp = 0;
                for(let j = startIdx; j < endIdx && j < totalPeaks; j++) {
                    if (this.peaks[j] > maxAmp) maxAmp = this.peaks[j];
                }
                
                const barHeight = maxAmp * this.height;
                const y = (this.height - barHeight) / 2;
                this.ctx.fillRect(x, y, 1, barHeight);
            }
        }
    }

    drawStatic() {
        if (!this.staticBuffer) return;
        
        // Clear
        this.ctx.fillStyle = this.fillStyle;
        this.ctx.fillRect(0, 0, this.width, this.height);

        const data = this.staticBuffer.getChannelData(0);
        const step = Math.ceil(data.length / this.width);
        // const amp = this.height / 2;

        this.ctx.fillStyle = '#0f0'; // Consistent style
        // this.ctx.lineWidth = 1;
        // this.ctx.strokeStyle = this.strokeStyle;
        this.ctx.beginPath();

        for (let i = 0; i < this.width; i++) {
            let maxAmp = 0;
            for (let j = 0; j < step; j++) {
                const datum = Math.abs(data[(i * step) + j]);
                if (datum > maxAmp) maxAmp = datum;
            }
            
            const barHeight = maxAmp * this.height;
            const y = (this.height - barHeight) / 2;
            this.ctx.fillRect(i, y, 1, barHeight);
        }
        // this.ctx.stroke();

        // Draw Playhead
        if (this.audioElement) {
            const duration = this.staticBuffer ? this.staticBuffer.duration : this.audioElement.duration;
            const progress = this.audioElement.currentTime / duration;
            // Guard against NaN or Infinity
            const cleanProgress = Number.isFinite(progress) ? progress : 0;
            const x = cleanProgress * this.width;
            
            this.ctx.strokeStyle = '#ffffff';
            this.ctx.lineWidth = 2;
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.height);
            this.ctx.stroke();
        }
    }
}
