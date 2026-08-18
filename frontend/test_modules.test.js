import test from 'node:test';
import assert from 'node:assert/strict';
import { average, standardDeviation, pushFeature } from './modules/capture.js';
import { fetchWithTimeout } from './modules/api.js';

test('average() returns correct mean for numbers', () => {
    assert.equal(average([100, 200, 300]), 200);
    assert.equal(average([]), 0);
    assert.equal(average([50]), 50);
});

test('standardDeviation() computes population standard deviation', () => {
    assert.equal(standardDeviation([]), 0);
    assert.equal(standardDeviation([10, 10, 10]), 0);
    // [10, 20] -> avg = 15, diffs = [-5, 5], sqDiffs = [25, 25], avgSq = 25, sqrt = 5
    assert.equal(standardDeviation([10, 20]), 5);
});

test('pushFeature() maintains max window length', () => {
    const times = [];
    const timestamps = [];
    pushFeature(times, timestamps, 10, 2);
    pushFeature(times, timestamps, 20, 2);
    pushFeature(times, timestamps, 30, 2);

    assert.deepEqual(times, [20, 30]);
    assert.equal(timestamps.length, 2);
});

test('fetchWithTimeout() successfully fetches valid URL', async () => {
    // Mock fetch for unit test isolation
    global.fetch = async (url, options) => {
        return {
            ok: true,
            status: 200,
            json: async () => ({ status: "healthy" })
        };
    };

    const res = await fetchWithTimeout("http://127.0.0.1:8000/health", {}, 1000);
    const data = await res.json();
    assert.equal(res.ok, true);
    assert.equal(data.status, "healthy");
});

test('fetchWithTimeout() aborts on timeout', async () => {
    global.fetch = (url, options) => {
        return new Promise((resolve, reject) => {
            options.signal.addEventListener('abort', () => {
                const err = new Error('The operation was aborted');
                err.name = 'AbortError';
                reject(err);
            });
        });
    };

    await assert.rejects(
        async () => {
            await fetchWithTimeout("http://127.0.0.1:8000/slow", {}, 50);
        },
        { name: 'AbortError' }
    );
});
