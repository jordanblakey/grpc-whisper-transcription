class Transcriber {
    constructor() {
        this.socket = null;
        this.isStreaming = false;
        this.historyDiv = document.getElementById('transcript-history');
        this.partialDiv = document.getElementById('partial-result');
        this.audioContext = null;
        this.processor = null;
        this.inputSource = null;
    }

    async start(stream, audioContext) {
        if (this.isStreaming) return;
        
        console.log('Starting Transcriber...');
        this.audioContext = audioContext;
        this.inputSource = this.audioContext.createMediaStreamSource(stream);

        // Refresh references since they might not be ready at construction
        this.historyDiv = document.getElementById('transcript-history');
        this.partialDiv = document.getElementById('partial-result');

        // Clear previous results
        if (this.historyDiv) this.historyDiv.innerHTML = '';
        if (this.partialDiv) this.partialDiv.textContent = '';

        try {
            // Initialize WebSocket
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            this.socket = new WebSocket(`${protocol}//${window.location.host}/ws/audio`);
            
            this.socket.onopen = () => {
                console.log('Transcriber WebSocket connected');
                this.socket.send(JSON.stringify({ sample_rate: this.audioContext.sampleRate }));
            };

            this.socket.onclose = () => {
                console.log('Transcriber WebSocket disconnected');
                this.isStreaming = false;
            };

            this.socket.onmessage = (event) => this.handleMessage(event);

            // Load AudioWorklet
            await this.audioContext.audioWorklet.addModule('/static/js/audio-processor.js');
            this.processor = new AudioWorkletNode(this.audioContext, 'audio-processor');

            this.inputSource.connect(this.processor);
            this.processor.connect(this.audioContext.destination);

            this.processor.port.onmessage = (event) => {
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                    this.socket.send(event.data.buffer);
                }
            };

            this.isStreaming = true;
        } catch (err) {
            console.error('Transcriber start error:', err);
        }
    }

    stop() {
        if (!this.isStreaming) return;
        console.log('Stopping Transcriber...');

        if (this.processor) {
            this.processor.disconnect();
            this.processor = null;
        }
        
        if (this.inputSource) {
            this.inputSource.disconnect();
            this.inputSource = null;
        }

        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
        
        this.isStreaming = false;
    }

    handleMessage(event) {
        const data = JSON.parse(event.data);
        const transcriptionDiv = document.getElementById('transcription'); 
        
        if (data.is_final) {
            this.partialDiv.textContent = '';
            
            const segment = document.createElement('div');
            segment.className = 'transcript-segment';
            
            const seconds = Math.floor(data.start_time);
            const mm = String(Math.floor(seconds / 60)).padStart(2, '0');
            const ss = String(seconds % 60).padStart(2, '0');
            const timestamp = `[${mm}:${ss}]`;
            
            segment.innerHTML = `<span class="timestamp">${timestamp}</span>${data.text}`;
            this.historyDiv.appendChild(segment);
        } else {
            this.partialDiv.textContent = data.text;
        }
        
        if (transcriptionDiv) {
            transcriptionDiv.scrollTop = transcriptionDiv.scrollHeight;
        }
    }
}
