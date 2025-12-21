class Recorder extends HTMLElement {
    constructor() {
        super();
        this.stream = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.audio = null;
        this.audioUrl = null;
        this.recordings = [];
        this.recordingStartTime = null;
        this.database = new RecorderDatabase();
        this.waveform = null;
    }

    connectedCallback() {
        this.render();
        this.recordButton = this.querySelector('#record');
        this.infoButton = this.querySelector('#info');
        this.clearAllButton = this.querySelector('#clear-all');
        this.playButton = this.querySelector('#play');
        this.saveButton = this.querySelector('#save');
        this.deleteButton = this.querySelector('#delete');
        this.recordingSelector = this.querySelector('#recordingSelector');
        this.statusDisplay = this.querySelector('#status');
        
        this.recordButton.addEventListener('click', () => this.record());
        this.infoButton.addEventListener('click', () => {
             if (!this.recordingDetails) {
                 this.recordingDetails = new RecordingDetails(this);
             }
             this.recordingDetails.toggle();
        });
        this.clearAllButton.addEventListener('click', () => this.clearAll());
        this.playButton.addEventListener('click', () => this.play());
        this.saveButton.addEventListener('click', () => this.save());
        this.deleteButton.addEventListener('click', () => this.delete());
        this.recordingSelector.addEventListener('change', (event) => this.selectRecording(event.target.value));
        
        const canvas = this.querySelector('#waveform-canvas');
        if (canvas) {
            // Wait for waveform.js to load if it hasn't already (simple check)
            if (typeof WaveformDisplay !== 'undefined') {
                this.waveform = new WaveformDisplay(canvas);
            } else {
                console.error("WaveformDisplay not defined. Make sure waveform.js is loaded.");
            }
        }

        this.renderRecordingSelector();

        // Hotkeys
        document.addEventListener('keydown', (e) => {
             if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

             if (e.code === 'Space') {
                 e.preventDefault();
                 if (this.audio) {
                     this.play();
                 }
             } else if (e.code === 'ArrowLeft') {
                 e.preventDefault();
                 if (this.audio) {
                     const duration = (Number.isFinite(this.audioDuration) ? this.audioDuration : this.audio.duration) || 0;
                     const step = duration * 0.10;
                     this.audio.currentTime = Math.max(0, this.audio.currentTime - step);
                 }
             } else if (e.code === 'ArrowRight') {
                 e.preventDefault();
                 if (this.audio) {
                     const duration = (Number.isFinite(this.audioDuration) ? this.audioDuration : this.audio.duration) || Infinity;
                     const step = (Number.isFinite(duration) ? duration : 10) * 0.10;
                     this.audio.currentTime = Math.min(duration, this.audio.currentTime + step);
                 }
             } else if ((e.key === 'r' || e.code === 'KeyR') && !e.ctrlKey && !e.metaKey) {
                 e.preventDefault();
                 this.record();
             } else if (e.key === 'x' || e.code === 'KeyX') {
                 // x for delete
                 if (this.recordingSelector.value) {
                     e.preventDefault();
                     this.delete();
                 }
             } else if (e.key === 's' || e.code === 'KeyS') {
                 // s for save
                 const isCtrlS = (e.ctrlKey || e.metaKey) && (e.key === 's' || e.code === 'KeyS');
                 if (this.recordingSelector.value && !isCtrlS) {
                     // Only trigger if specifically just 's', let browser handle ctrl+s if user wants
                     // But user asked for 's' hotkey, usually implies simple 's'
                     e.preventDefault();
                     this.save();
                 } 
             } else if (e.key === 'i' || e.code === 'KeyI') {
                 // i for info
                 if (!this.recordingDetails) {
                     this.recordingDetails = new RecordingDetails(this);
                 }
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
             }
        });
    }
        
    render() {
        this.innerHTML = `
        <div id="controls">
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
        <div id="player">
            <canvas id="waveform-canvas" title="Click to seek, Arrow Left/Right to seek +/- 10%" style="width: 100%; height: 100px; background: #000; display: block; margin-bottom: 10px;"></canvas>
            <pre id="status">No recording selected.</pre>
        </div>

        `;
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
                if (this.recordings.length > 0) {
                     targetId = this.recordings[0].id;
                }
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
            if (this.audio.duration !== Infinity && !isNaN(this.audio.duration)) {
                return resolve();
            }
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

    async record() {
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.recordButton.textContent = "🔴";
            this.stopRecording();
            return;
        } else {
            this.recordButton.textContent = "⬛";
        }
        
        this.cleanUpRecorder();
        this.stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: false,
                noiseSuppression: false,
                autoGainControl: true
            }
        });
        this.mediaRecorder = new MediaRecorder(this.stream);
        this.mediaRecorder.start(1000 / 60);
        const audioContext = new AudioContext();
        const source = audioContext.createMediaStreamSource(this.stream);
        this.analyzer = audioContext.createAnalyser();
        this.analyzer.fftSize = 256;
        source.connect(this.analyzer);
        
        if (this.waveform) {
            this.waveform.connect(this.analyzer);
        }
        
        // Initialize RecordingDetails
        if (!this.recordingDetails) {
            this.recordingDetails = new RecordingDetails(this);
        }

        this.recordingStartTime = Date.now();
        this.mediaRecorder.ondataavailable = event => {
            this.audioChunks.push(event.data);
            this.renderRecorderInfo();
            if (this.recordingDetails) {
                 this.recordingDetails.update(this.stream, this.mediaRecorder, this.analyzer, this.recordingStartTime);
            }
        };
    }

    stopRecording() {
        this.mediaRecorder.onstop = async () => {
            const mimeType = this.mediaRecorder.mimeType || 'audio/webm';
            const audioBlob = new Blob(this.audioChunks, { type: mimeType });
            const timestamp = Date.now();
            await this.database.addRecording(audioBlob, timestamp);
            await this.renderRecordingSelector(timestamp, true);
            this.stream.getTracks().forEach(track => track.stop());
        }
        this.mediaRecorder.stop();

    }

    cleanUpRecorder() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
        if (this.mediaRecorder) {
            this.mediaRecorder.stop();
        }
        if (this.waveform && this.waveform.isLive) {
            this.waveform.stopLoop();
        }
        this.audioChunks = [];
        this.audio = null;
    }   

    play() {
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
        this.audio.onended = updatePlayButton;
        updatePlayButton();
    }

    save() {
        if (this.audioUrl) {
           const a = document.createElement('a');
           a.href = this.audioUrl;
           const timestamp = this.recordingSelector.value || Date.now();
           a.download = `recording-${timestamp}.webm`; // Or infer extension from blob
           document.body.appendChild(a);
           a.click();
           document.body.removeChild(a);
        }
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
        
        // Clear details unless specifically asked to preserve (e.g. just finished recording)
        if (!preserveDetails && this.recordingDetails) {
            this.recordingDetails.clear();
        }

        const recording = await this.database.getRecording(value);
        this.audioUrl && URL.revokeObjectURL(this.audioUrl);
        this.audioUrl = URL.createObjectURL(recording.blob);
        this.audio = new Audio(this.audioUrl);
        
        if (this.waveform) {
            const context = new AudioContext(); // Decoding requires context
            const arrayBuffer = await recording.blob.arrayBuffer();
            const audioBuffer = await context.decodeAudioData(arrayBuffer);
            this.waveform.load(audioBuffer);
            this.waveform.bindAudio(this.audio);
            
            // Fix Infinity duration by using decoded buffer duration
            this.audioDuration = audioBuffer.duration;
            // Initial state for newly selected recording
            this.renderPlayerInfo();
            
            // Update time on seek/timeupdate
            this.audio.addEventListener('timeupdate', () => {
                if(this.audio.paused) {
                    this.renderPlayerInfo();
                }
            });
        }

    }


}

customElements.define('audio-recorder', Recorder);
document.body.appendChild(new Recorder());
