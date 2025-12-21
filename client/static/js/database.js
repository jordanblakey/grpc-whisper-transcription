class RecorderDatabase {
    constructor() {
        this.db = null;
        this.initPromise = this.init();
    }

    init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('recorder', 1);
            request.onerror = (event) => {
                console.error("Database error: " + event.target.errorCode);
                reject(event);
            };
            request.onsuccess = (event) => {
                this.db = event.target.result;
                resolve(this.db);
            };
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                db.createObjectStore('recordings', { keyPath: 'id' });
            };
        });
    }

    close() {
        if (this.db) {
            this.db.close();
        }
    }

    async addRecording(blob, timestamp) {
        await this.initPromise;
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['recordings'], 'readwrite');
            const store = transaction.objectStore('recordings');
            const request = store.put({id: timestamp, blob: blob});
            request.onerror = (event) => {
                reject(event);
            };
            request.onsuccess = (event) => {
                resolve(event);
            };
        });
    }

    async deleteRecording(id) {
        await this.initPromise;
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['recordings'], 'readwrite');
            const store = transaction.objectStore('recordings');
            const request = store.delete(Number(id));
            request.onerror = (event) => {
                reject(event);
            };
            request.onsuccess = (event) => {
                resolve(event);
            };
        });
    }

    async getRecording(id) {
        await this.initPromise;
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['recordings'], 'readonly');
            const store = transaction.objectStore('recordings');
            const request = store.get(Number(id));
            request.onerror = (event) => {
                reject(event);
            };
            request.onsuccess = (event) => {
                resolve(event.target.result);
            };
        });
    }

    async getRecordings() {
        await this.initPromise;
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['recordings'], 'readonly');
            const store = transaction.objectStore('recordings');
            const request = store.getAll();
            request.onerror = (event) => {
                reject(event);
            };
            request.onsuccess = (event) => {
                resolve(event.target.result);
            };
        });
    }

    async clear() {
        await this.initPromise;
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['recordings'], 'readwrite');
            const store = transaction.objectStore('recordings');
            const request = store.clear();
            request.onerror = (event) => {
                reject(event);
            };
            request.onsuccess = (event) => {
                resolve(event);
            };
        });
    }
}