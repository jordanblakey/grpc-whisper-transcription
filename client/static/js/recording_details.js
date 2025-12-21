class RecordingDetails {
    constructor(container) {
        this.container = container;
        this.isVisible = false;
        
        // Create UI elements
        this.panel = document.createElement('div');
        this.panel.style.display = 'none';
        this.panel.style.border = '1px solid #ccc';
        this.panel.style.padding = '10px';
        this.panel.style.marginTop = '10px';
        this.panel.style.backgroundColor = '#f9f9f9';
        this.panel.style.fontFamily = 'monospace';
        this.panel.style.overflowX = 'auto'; // Handle wide pre tags
        this.panel.style.color = 'black'; // Ensure text is visible
        
        this.container.appendChild(this.panel);
    }

    toggle() {
        this.isVisible = !this.isVisible;
        this.panel.style.display = this.isVisible ? 'block' : 'none';
        return this.isVisible;
    }

    clear() {
        this.panel.replaceChildren();
    }

    update(stream, mediaRecorder, analyzer, recordingStartTime) {
        if (!this.isVisible || !stream) return;

        this.panel.replaceChildren();

        const tracks = stream.getAudioTracks();
        if (tracks.length === 0) return;
        const track = tracks[0];

        // Level
        const dataArray = new Uint8Array(analyzer.frequencyBinCount);
        analyzer.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((prev, curr) => prev + curr, 0) / dataArray.length;
        const EstimatedSoundPressureLevelDb = average + 33;

        // Info blocks
        this.addBlock(`recordingDuration: ${((Date.now() - recordingStartTime) / 1000).toFixed(2)}s`);
        this.addBlock(`EstimatedSoundPressureLevelDb: ${(EstimatedSoundPressureLevelDb).toFixed(2)}`);
        
        this.addBlock(`track.id: ${track.id}`);
        this.addBlock(`track.kind: ${track.kind}`);
        this.addBlock(`track.label: ${track.label}`);
        this.addBlock(`track.muted: ${track.muted}`);
        this.addBlock(`track.enabled: ${track.enabled}`);

        this.addSection('settings:', track.getSettings());
        this.addSection('constraints:', track.getConstraints());
        // Note: track.stats isn't standard, usually it's getStats(), but copying existing logic for now
        if (track.stats) this.addSection('stats:', track.stats); 

        const analyzerStr = `analyzer.frequencyBinCount: ${analyzer.frequencyBinCount}\n` +
                            `analyzer.fftSize: ${analyzer.fftSize}\n` +
                            `analyzer.maxDecibels: ${analyzer.maxDecibels}\n` +
                            `analyzer.minDecibels: ${analyzer.minDecibels}\n` +
                            `analyzer.smoothingTimeConstant: ${analyzer.smoothingTimeConstant}\n` +
                            `analyzer.channelInterpretation: ${analyzer.channelInterpretation}`;
        
        this.addBlock('analyzer:\n' + analyzerStr);
    }

    addBlock(text) {
        const div = document.createElement('div');
        div.textContent = text;
        div.style.whiteSpace = 'pre-wrap';
        this.panel.appendChild(div);
    }

    addSection(title, data) {
        const pre = document.createElement('pre');
        pre.textContent = title + '\n' + JSON.stringify(data, null, 2);
        pre.style.margin = '5px 0';
        this.panel.appendChild(pre);
    }
}
