const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync(require.resolve('../web/audio-utils.js'), 'utf8');
vm.runInThisContext(source, { filename: 'audio-utils.js' });

async function main() {
  const audioBuffer = {
    numberOfChannels: 2,
    length: 3,
    sampleRate: 16000,
    getChannelData(index) {
      return index === 0
        ? new Float32Array([0, 1, -1])
        : new Float32Array([0, 0.5, -0.5]);
    },
  };

  const wav = globalThis.LiveTalkingAudio.audioBufferToWavBlob(audioBuffer);
  assert.equal(wav.type, 'audio/wav');

  const bytes = Buffer.from(await wav.arrayBuffer());
  assert.equal(bytes.toString('ascii', 0, 4), 'RIFF');
  assert.equal(bytes.toString('ascii', 8, 12), 'WAVE');
  assert.equal(bytes.toString('ascii', 12, 16), 'fmt ');
  assert.equal(bytes.readUInt16LE(20), 1, 'must use PCM encoding');
  assert.equal(bytes.readUInt16LE(22), 1, 'must downmix to mono');
  assert.equal(bytes.readUInt32LE(24), 16000);
  assert.equal(bytes.readUInt16LE(34), 16);
  assert.equal(bytes.toString('ascii', 36, 40), 'data');
  assert.equal(bytes.readUInt32LE(40), 6);
  assert.deepEqual(
    [bytes.readInt16LE(44), bytes.readInt16LE(46), bytes.readInt16LE(48)],
    [0, 24575, -24576],
  );
}

main().then(() => console.log('浏览器录音 WAV 编码测试通过'));
