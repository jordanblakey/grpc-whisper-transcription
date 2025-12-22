class Recorder extends HTMLElement {
    constructor() {
        super();
        this.stream = null;
        this.audioContext = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.audio = null;
        this.audioUrl = null;
        this.recordings = [];
        this.recordingStartTime = null;
        
        this.database = new RecorderDatabase();
        
        // Modules
        this.waveform = null; // Legacy playback/recording waveform
        this.visualizer = new AudioVisualizer();
        this.transcriber = new Transcriber();
        this.recordingDetails = null;

        // States
        this.isStreaming = false;
        this.visualizerState = 'HIDDEN'; // HIDDEN, VISIBLE, PAUSED
    }

    connectedCallback() {
        this.render();
        this.bindElements();
        this.bindEvents();
        
        // Initialize waveform if script loaded
        const canvas = this.querySelector('#waveform-canvas');
        if (canvas && typeof WaveformDisplay !== 'undefined') {
            this.waveform = new WaveformDisplay(canvas);
        }

        this.renderRecordingSelector();
        
        // Auto-show visualizer
        this.toggleVisualizer();
    }
        
    render() {
        this.innerHTML = `
        <div id="controls">
            <div class="row">
                <button id="record" title="Record (r)">🔴</button>
                <button id="info" title="Show Recording Details (i)">ℹ️</button>
                <select id="recordingSelector" title="Select Recording (Up/Down Arrows)">
                    <option value="">Select a recording</option>
                </select>
                <button id="play" title="Play/Pause (Space)">▶️</button>
                <button id="save" title="Save Recording (s)">💾</button>
                <button id="delete" title="Delete Recording (x)">🗑️</button>
                <button id="clear-all" title="Clear All Recordings">🧼✨</button>
            </div>
            <div class="row" style="margin-top: 10px;">
                <button id="stream-btn" title="Start Transcribing (t)">Start Transcribing</button>
                <button id="visualizer-btn" title="Toggle Visualizer (v)">Show Visualizer</button>
            </div>
        </div>

        <div id="visualizer-container" style="display: none; margin-bottom: 20px;">
            <div class="canvas-container" id="waveform-container" style="height: 100px;">
                <canvas id="waveform"></canvas>
                <canvas id="waveform-ui" class="overlay"></canvas>
            </div>
            <div class="canvas-container" id="spectrum-container" style="height: 100px;">
                <canvas id="freq-spectrum"></canvas>
                <canvas id="freq-spectrum-ui" class="overlay"></canvas>
            </div>
            <div class="canvas-container" id="spectrogram-container" style="height: 200px;">
                <canvas id="spectrogram"></canvas>
                <canvas id="spectrogram-ui" class="overlay"></canvas>
            </div>
        </div>

        <div id="transcription-container" style="margin-bottom: 20px; text-align: left;">
            <div id="transcription">
                <div id="transcript-history"></div>
                <div id="partial-result"></div>
            </div>
        </div>

        <div id="player">
            <canvas id="waveform-canvas" title="Click to seek, Arrow Left/Right to seek +/- 10%" style="width: 100%; height: 100px; background: #000; display: block; margin-bottom: 10px;"></canvas>
            <pre id="status">No recording selected.</pre>
        </div>
        `;
    }

    bindElements() {
        this.recordButton = this.querySelector('#record');
        this.streamButton = this.querySelector('#stream-btn');
        this.visualizerButton = this.querySelector('#visualizer-btn');
        this.infoButton = this.querySelector('#info');
        this.clearAllButton = this.querySelector('#clear-all');
        this.playButton = this.querySelector('#play');
        this.saveButton = this.querySelector('#save');
        this.deleteButton = this.querySelector('#delete');
        this.recordingSelector = this.querySelector('#recordingSelector');
        this.statusDisplay = this.querySelector('#status');
        this.visualizerContainer = this.querySelector('#visualizer-container');
    }

    bindEvents() {
        this.recordButton.addEventListener('click', () => this.record());
        this.streamButton.addEventListener('click', () => this.toggleStreaming());
        this.visualizerButton.addEventListener('click', () => this.toggleVisualizer());
        
        this.infoButton.addEventListener('click', () => {
             if (!this.recordingDetails) this.recordingDetails = new RecordingDetails(this);
             this.recordingDetails.toggle();
        });
        
        this.clearAllButton.addEventListener('click', () => this.clearAll());
        this.playButton.addEventListener('click', () => this.play());
        this.saveButton.addEventListener('click', () => this.save());
        this.deleteButton.addEventListener('click', () => this.delete());
        this.recordingSelector.addEventListener('change', (event) => this.selectRecording(event.target.value));

        // Hotkeys
        document.addEventListener('keydown', (e) => this.handleHotkey(e));
    }

    handleHotkey(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        if (e.code === 'Space') {
            e.preventDefault();
            if (this.audio) this.play();
        } else if (e.code === 'ArrowLeft') {
            e.preventDefault();
            if (this.audio) {
                const duration = (Number.isFinite(this.audioDuration) ? this.audioDuration : this.audio.duration) || 0;
                this.audio.currentTime = Math.max(0, this.audio.currentTime - (duration * 0.10));
            }
        } else if (e.code === 'ArrowRight') {
            e.preventDefault();
            if (this.audio) {
                const duration = (Number.isFinite(this.audioDuration) ? this.audioDuration : this.audio.duration) || Infinity;
                if (Number.isFinite(duration)) {
                     this.audio.currentTime = Math.min(duration, this.audio.currentTime + (duration * 0.10));
                }
            }
        } else if (e.key.toLowerCase() === 'r' && !e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            this.record();
        } else if (e.key.toLowerCase() === 'x') {
            if (this.recordingSelector.value) {
                e.preventDefault();
                this.delete();
            }
        } else if (e.key.toLowerCase() === 's') {
            const isCtrlS = (e.ctrlKey || e.metaKey);
            if (this.recordingSelector.value && !isCtrlS) {
                e.preventDefault();
                this.save();
            } 
        } else if (e.key.toLowerCase() === 'i') {
            if (!this.recordingDetails) this.recordingDetails = new RecordingDetails(this);
            this.recordingDetails.toggle();
        } else if (e.code === 'ArrowUp') {
            e.preventDefault();
            if (this.recordingSelector.selectedIndex > 0) {
                this.recordingSelector.selectedIndex--;
                this.selectRecording(this.recordingSelector.value);
            }
        } else if (e.code === 'ArrowDown') {
            e.preventDefault();
            if (this.recordingSelector.selectedIndex < this.recordingSelector.options.length - 1) {
                this.recordingSelector.selectedIndex++;
                this.selectRecording(this.recordingSelector.value);
            }
        } else if (e.key.toLowerCase() === 't' && !e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            this.toggleStreaming();
        } else if (e.key.toLowerCase() === 'v' && !e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            this.toggleVisualizer();
        }
    }

    async getMicrophone() {
        if (this.stream) return this.stream;

        // Initialize AudioContext if needed
        if (!this.audioContext || this.audioContext.state === 'closed') {
             this.audioContext = new AudioContext();
        }
        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }

        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: false,
                    noiseSuppression: false,
                    autoGainControl: true
                }
            });
            return this.stream;
        } catch (err) {
            console.error('Error accessing microphone:', err);
            return null;
        }
    }

    checkMicrophoneUsage() {
        const recording = (this.mediaRecorder && this.mediaRecorder.state === 'recording');
        // Keep mic if Recording OR Streaming OR Visualizer is VISIBLE
        // If Visualizer is PAUSED, we don't strictly *need* mic data, so we can release it if nothing else needs it.
        if (!recording && !this.isStreaming && this.visualizerState !== 'VISIBLE') {
            // Stop tracks to release microphone
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
                this.stream = null;
            }
            // Note: We might want to keep AudioContext alive or close it
        }
    }

    async toggleStreaming() {
        if (this.isStreaming) {
            this.transcriber.stop();
            this.isStreaming = false;
            this.streamButton.textContent = "Start Transcribing";
            this.streamButton.classList.remove('active');
            this.checkMicrophoneUsage();
        } else {
            const stream = await this.getMicrophone();
            if (!stream) return;
            
            await this.transcriber.start(stream, this.audioContext);
            this.isStreaming = true;
            this.streamButton.textContent = "Stop Transcribing";
            this.streamButton.classList.add('active');
        }
    }

    async toggleVisualizer() {
        if (this.visualizerState === 'VISIBLE') {
            // Go to PAUSED
            this.visualizer.stop();
            this.visualizerState = 'PAUSED';
            this.visualizerButton.textContent = "Hide Visualizer";
            // Microphone keeps running if recording/transcribing, or if we consider PAUSED "using" it?
            // Actually PAUSED means we don't need new data.
            this.checkMicrophoneUsage(); 
        } else if (this.visualizerState === 'PAUSED') {
            // Go to HIDDEN
            this.visualizer.stop(); // Ensure stopped
            this.visualizerState = 'HIDDEN';
            this.visualizerContainer.style.display = 'none';
            this.visualizerButton.textContent = "Show Visualizer";
            this.checkMicrophoneUsage();
        } else {
            // HIDDEN (or undefined) -> Go to VISIBLE
            const stream = await this.getMicrophone();
            if (!stream) return;

            if (!this.visualizer.waveCanvas) {
                this.visualizer = new AudioVisualizer();
            }

            this.visualizerContainer.style.display = 'block';
            this.visualizer.start(stream, this.audioContext);
            this.visualizerState = 'VISIBLE';
            this.visualizerButton.textContent = "Pause Visualizer";
        }
    }

    async record() {
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.recordButton.textContent = "🔴";
            this.stopRecording();
            return;
        }

        const stream = await this.getMicrophone();
        if (!stream) return;

        this.recordButton.textContent = "⬛";
        
        this.mediaRecorder = new MediaRecorder(stream);
        this.mediaRecorder.start(1000 / 60);

        // Analyzer for RecordingDetails/Progress Waveform
        // Note: We create a NEW analyser for the Recorder's own visualization purposes
        // This is separate from AudioVisualizer
        const source = this.audioContext.createMediaStreamSource(stream);
        this.analyzer = this.audioContext.createAnalyser();
        this.analyzer.fftSize = 256;
        source.connect(this.analyzer);
        
        if (this.waveform) {
            this.waveform.connect(this.analyzer);
        }
        
        if (!this.recordingDetails) this.recordingDetails = new RecordingDetails(this);

        this.recordingStartTime = Date.now();
        this.mediaRecorder.ondataavailable = event => {
            this.audioChunks.push(event.data);
            this.renderRecorderInfo();
            if (this.recordingDetails) {
                 this.recordingDetails.update(stream, this.mediaRecorder, this.analyzer, this.recordingStartTime);
            }
        };
    }

    stopRecording() {
        if (!this.mediaRecorder) return;
        
        this.mediaRecorder.onstop = async () => {
            if (this.audioChunks.length === 0) {
                console.warn("No audio chunks recorded.");
                return;
            }
            
            const mimeType = this.mediaRecorder.mimeType || 'audio/webm';
            const audioBlob = new Blob(this.audioChunks, { type: mimeType });
            const timestamp = Date.now();
            await this.database.addRecording(audioBlob, timestamp);
            await this.renderRecordingSelector(timestamp, true);
            
            // Clean up recorder-specific tracks/analyzer?
            // Actually, since we share 'stream', we should NOT stop tracks here if others are using it.
            // But 'getMicrophone' returns the shared stream.
            // If we stop tracks here, we break Streaming/Visualizer.
            // SO: WE MUST NOT CALL track.stop() HERE.
            
            this.checkMicrophoneUsage();
            this.audioChunks = []; // Clean up AFTER saving
        };

        this.mediaRecorder.stop();
        // Specific cleanup for waveform/analyzer
         if (this.waveform && this.waveform.isLive) {
            this.waveform.stopLoop();
        }
    }

    renderRecordingSelector(activeId = null, preserveDetails = false) {
        return this.database.getRecordings().then(async recordings => {
            this.recordings = recordings.sort((a, b) => b.id - a.id);
            this.recordingSelector.replaceChildren();
            this.recordingSelector.appendChild(new Option('Select a recording', ''));
            this.recordings.forEach(recording => {
                const option = new Option(new Date(recording.id).toLocaleString(), recording.id);        
                this.recordingSelector.appendChild(option);
            });
            
            let targetId = activeId;
            if (!targetId && !this.recordingSelector.value) {
                if (this.recordings.length > 0) targetId = this.recordings[0].id;
            }
            
            if (targetId) {
                await this.selectRecording(targetId, preserveDetails);
            } else {
                await this.selectRecording('', preserveDetails);
            }
        });
    }

    renderRecorderInfo() {
        const duration = ((Date.now() - this.recordingStartTime) / 1000).toFixed(2);
        this.statusDisplay.textContent = `Recording (Time: ${duration}s)`;
    }

    formatTime(seconds) {
        const minutes = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
        const secs = String((seconds % 60).toFixed(2)).padStart(5, '0');
        return `${minutes}:${secs}`;
    }

    async renderPlayerInfo() {
        let duration = this.audioDuration;
        if (!Number.isFinite(duration)) {
             await this.getDuration();
             duration = this.audio.duration;
        }
        const current = this.formatTime(this.audio.currentTime);
        const total = this.formatTime(duration);
        const state = this.audio.paused ? "Paused" : "Playing";
        this.statusDisplay.textContent = `${state} (Time: ${current} / ${total})`;
        if (this.audio && !this.audio.paused) {
            this.animationFrameId = requestAnimationFrame(() => this.renderPlayerInfo());
        }
    }

    async getDuration() {
        await new Promise((resolve) => {
            if (this.audio.duration !== Infinity && !isNaN(this.audio.duration)) return resolve();
            this.audio.addEventListener('loadedmetadata', () => {
                this.audio.addEventListener('timeupdate', () => {
                    this.audio.currentTime = 0;
                    this.audio.muted = false;
                    resolve();
                }, { once: true });
                this.audio.muted = true;
                this.audio.currentTime = 1e101;
            });
        });
    }

    delete() {
        this.database.deleteRecording(this.recordingSelector.value);
        this.renderRecordingSelector();
    }

    clearAll() {
        this.database.clear();
        this.renderRecordingSelector();
    }

    async selectRecording(value, preserveDetails = false) {
        if (!value) {
            this.audioUrl && URL.revokeObjectURL(this.audioUrl);
            this.audioUrl = null;
            this.audio = null;
            if (this.waveform) this.waveform.clear();
            if (this.recordingDetails) this.recordingDetails.clear();
            this.statusDisplay.textContent = 'No recording selected.';
            this.recordingSelector.value = '';
            return;
        }
        this.recordingSelector.value = value;
        if (this.audio && !this.audio.paused) {
            this.audio.pause();
            this.playButton.textContent = "▶️";
        }
        if (!preserveDetails && this.recordingDetails) this.recordingDetails.clear();

        const recording = await this.database.getRecording(value);
        this.audioUrl && URL.revokeObjectURL(this.audioUrl);
        this.audioUrl = URL.createObjectURL(recording.blob);
        this.audio = new Audio(this.audioUrl);
        
        if (this.waveform) {
            try {
                const context = new AudioContext(); 
                const arrayBuffer = await recording.blob.arrayBuffer();
                if (arrayBuffer.byteLength === 0) throw new Error("Empty audio buffer");
                
                const audioBuffer = await context.decodeAudioData(arrayBuffer);
                this.waveform.load(audioBuffer);
                this.waveform.bindAudio(this.audio);
                this.audioDuration = audioBuffer.duration;
                this.renderPlayerInfo();
                this.audio.addEventListener('timeupdate', () => {
                    if(this.audio.paused) this.renderPlayerInfo();
                });
            } catch (err) {
                console.error("Error loading audio for waveform:", err);
                this.statusDisplay.textContent = "Error: Invalid or empty audio file.";
                if (this.waveform) this.waveform.clear();
            }
        }
    }
    
    play() {
        if (!this.audio) return;
        
        const updatePlayButton = event => {
            if (event || !this.audio.paused) {
                this.audio.pause();
                this.playButton.textContent = "▶️";
                cancelAnimationFrame(this.animationFrameId);
            } else {
                this.audio.play();
                this.playButton.textContent = "⏸️";
                this.renderPlayerInfo();
            }
        }
        
        // Remove previous listener to avoid duplicates if play called multiple times?
        // Actually onended is a property, so it overwrites.
        this.audio.onended = updatePlayButton;
        updatePlayButton();
    }
    
    save() {
        if (this.audioUrl) {
           const a = document.createElement('a');
           a.href = this.audioUrl;
           const timestamp = this.recordingSelector.value || Date.now();
           a.download = `recording-${timestamp}.webm`; 
           document.body.appendChild(a);
           a.click();
           document.body.removeChild(a);
        }
    }
}

customElements.define('audio-recorder', Recorder);
document.body.appendChild(new Recorder());
