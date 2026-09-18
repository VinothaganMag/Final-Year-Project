const DEFAULT_ANALYZER = 'http://127.0.0.1:5000';

const input = document.getElementById('origin');
const status = document.getElementById('status');

chrome.storage.local.get('analyzerOrigin').then((stored) => {
    input.value = stored.analyzerOrigin || DEFAULT_ANALYZER;
});

document.getElementById('save').addEventListener('click', async () => {
    const value = input.value.trim().replace(/\/+$/, '') || DEFAULT_ANALYZER;
    await chrome.storage.local.set({ analyzerOrigin: value });
    status.textContent = 'Saved.';
    setTimeout(() => { status.textContent = ''; }, 2000);
});
