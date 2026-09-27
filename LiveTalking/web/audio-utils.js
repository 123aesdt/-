(function (global) {
    'use strict';

    function writeAscii(view, offset, text) {
        for (let index = 0; index < text.length; index += 1) {
            view.setUint8(offset + index, text.charCodeAt(index));
        }
    }

    function audioBufferToWavBlob(audioBuffer) {
        const channelCount = audioBuffer.numberOfChannels;
        const sampleCount = audioBuffer.length;
        const mono = new Float32Array(sampleCount);

        for (let channel = 0; channel < channelCount; channel += 1) {
            const samples = audioBuffer.getChannelData(channel);
            for (let index = 0; index < sampleCount; index += 1) {
                mono[index] += samples[index] / channelCount;
            }
        }

        const buffer = new ArrayBuffer(44 + sampleCount * 2);
        const view = new DataView(buffer);
        writeAscii(view, 0, 'RIFF');
        view.setUint32(4, 36 + sampleCount * 2, true);
        writeAscii(view, 8, 'WAVE');
        writeAscii(view, 12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, 1, true);
        view.setUint32(24, audioBuffer.sampleRate, true);
        view.setUint32(28, audioBuffer.sampleRate * 2, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeAscii(view, 36, 'data');
        view.setUint32(40, sampleCount * 2, true);

        for (let index = 0; index < sampleCount; index += 1) {
            const sample = Math.max(-1, Math.min(1, mono[index]));
            view.setInt16(44 + index * 2, sample < 0 ? sample * 32768 : sample * 32767, true);
        }

        return new Blob([buffer], { type: 'audio/wav' });
    }

    async function recordedBlobToWav(blob) {
        const AudioContextClass = global.AudioContext || global.webkitAudioContext;
        if (!AudioContextClass) throw new Error('当前浏览器不支持音频解码');
        const context = new AudioContextClass();
        try {
            const decoded = await context.decodeAudioData(await blob.arrayBuffer());
            return audioBufferToWavBlob(decoded);
        } finally {
            await context.close();
        }
    }

    global.LiveTalkingAudio = { audioBufferToWavBlob, recordedBlobToWav };
})(globalThis);
