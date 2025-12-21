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
        console.log(this);
    }

    connectedCallback() {
        this.render();
        this.recordButton = this.querySelector('#record');
        this.clearAllButton = this.querySelector('#clear-all');
        this.playButton = this.querySelector('#play');
        this.deleteButton = this.querySelector('#delete');
        this.recordingSelector = this.querySelector('#recordingSelector');
        this.recorderInfo = this.querySelector('#recorderInfo');
        this.playerInfo = this.querySelector('#playerInfo');
        
        this.recordButton.addEventListener('click', () => this.record());
        this.clearAllButton.addEventListener('click', () => this.clearAll());
        this.playButton.addEventListener('click', () => this.play());
        this.deleteButton.addEventListener('click', () => this.delete());
        this.recordingSelector.addEventListener('click', (event) => this.selectRecording(event.target.value));
        this.renderRecordingSelector();
    }
        
    render() {
        this.innerHTML = `
        <div id="recorder">
            <h3>Recorder</h3>
            <button id="record">🔴</button>
            <pre id="recorderInfo"></pre>
        </div>
        <div id="player">
            <h3>Player</h3>
            <select id="recordingSelector">
                <option value="">Select a recording</option>
            </select>
            <button id="play">▶️</button>
            <button id="delete">🗑️</button>
            <button id="clear-all">🧼✨</button>
            <pre id="playerInfo"></pre>
        </div>

        `;
    }

    renderRecordingSelector() {
        return this.database.getRecordings().then(recordings => {
            this.recordings = recordings.sort((a, b) => b.id - a.id);
            this.recordingSelector.replaceChildren();
            this.recordingSelector.appendChild(new Option('Select a recording', ''));
            this.recordings.forEach(recording => {
                const option = new Option(new Date(recording.id).toLocaleString(), recording.id);        
                this.recordingSelector.appendChild(option);
            });
            if (!this.recordingSelector.value && this.recordings.length > 0) {
                this.selectRecording(this.recordings[0].id);
            }
        });
    }

    renderrecorderInfo() {
        this.recorderInfo.replaceChildren();
        this.recorderInfo.textContent += `State: ${this.mediaRecorder.state}, `;
        this.recorderInfo.textContent += `Duration: ${((Date.now() - this.recordingStartTime) / 1000).toFixed(2)}s\n`;
    }

    async renderPlayerInfo() {
        this.playerInfo.replaceChildren();

        await this.getDuration();
        const formatSeconds = seconds => {
            const minutes = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
            seconds = String((seconds % 60).toFixed(2)).padStart(5, '0');
            return `${minutes}:${seconds}`;
        };

        this.playerInfo.textContent += `${formatSeconds(this.audio.currentTime)} / `;
        this.playerInfo.textContent += `${formatSeconds(this.audio.duration)}`;

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
        this.stream = await navigator.mediaDevices.getUserMedia({audio: true});
        this.mediaRecorder = new MediaRecorder(this.stream);
        this.mediaRecorder.start(1000 / 60);
        const audioContext = new AudioContext();
        const source = audioContext.createMediaStreamSource(this.stream);
        this.analyzer = audioContext.createAnalyser();
        this.analyzer.fftSize = 256;
        source.connect(this.analyzer);
        this.recordingStartTime = Date.now();
        this.mediaRecorder.ondataavailable = event => {
            this.audioChunks.push(event.data);
            this.renderrecorderInfo();
        };
    }

    stopRecording() {
        this.mediaRecorder.onstop = async () => {
            const mimeType = this.mediaRecorder.mimeType || 'audio/webm';
            console.log(`Recorder stopped. MIME type: ${mimeType}, total chunks: ${this.audioChunks.length}`);
            const audioBlob = new Blob(this.audioChunks, { type: mimeType });
            const timestamp = Date.now();
            await this.database.addRecording(audioBlob, timestamp);
            await this.renderRecordingSelector();
            this.cleanUpRecorder();
        };
        this.mediaRecorder.stop();

    }

    cleanUpRecorder() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
        if (this.mediaRecorder) {
            this.mediaRecorder.stop();
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
                this.animationFrameId = requestAnimationFrame(() => {
                    this.renderPlayerInfo()
                });
            }
        }
        this.audio.onended = updatePlayButton;
        updatePlayButton();
    }

    delete() {
        this.database.deleteRecording(this.recordingSelector.value);
        this.audioUrl && URL.revokeObjectURL(this.audioUrl);
        this.audio = null;
        this.renderRecordingSelector();
    }

    clearAll() {
        this.database.clear();
        this.audioUrl &&  URL.revokeObjectURL(this.audioUrl);
        this.audio = null;
        this.renderRecordingSelector();
    }

    async selectRecording(value) {
        if (!value) {
            return;
        }
        this.recordingSelector.value = value;
        if (this.audio && !this.audio.paused) {
            this.audio.pause();
            this.playButton.textContent = "▶️";
        }
        const recording = await this.database.getRecording(value);
        this.audioUrl && URL.revokeObjectURL(this.audioUrl);
        this.audioUrl = URL.createObjectURL(recording.blob);
        this.audio = new Audio(this.audioUrl);
        this.renderPlayerInfo();
    }


}

customElements.define('audio-recorder', Recorder);
document.body.appendChild(new Recorder());

class Recording {
    constructor(id, name) {
        this.id = id;
        this.name = name;
    }
}