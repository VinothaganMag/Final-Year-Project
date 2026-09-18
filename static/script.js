// Dashboard Logic

// Example data for stats
const stats = {
    totalScans: 120,
    phishingDetected: 45,
    safeUrls: 75,
    accuracy: 92.5
};

// Populate stats
function populateStats() {
    document.getElementById('total-scans').textContent = stats.totalScans;
    document.getElementById('phishing-detected').textContent = stats.phishingDetected;
    document.getElementById('safe-urls').textContent = stats.safeUrls;
    document.getElementById('accuracy').textContent = `${stats.accuracy}%`;
}

// Example data for recent activity
const recentActivity = [
    { input: 'http://example.com', type: 'URL', result: 'Safe', confidence: '95%', time: '2026-04-06 10:00' },
    { input: 'http://phishing.com', type: 'URL', result: 'Phishing', confidence: '87%', time: '2026-04-06 09:45' },
    { input: 'Suspicious message content', type: 'Message', result: 'Phishing', confidence: '90%', time: '2026-04-06 09:30' },
    { input: 'http://safe-site.com', type: 'URL', result: 'Safe', confidence: '98%', time: '2026-04-06 09:15' },
    { input: 'Another suspicious message', type: 'Message', result: 'Phishing', confidence: '85%', time: '2026-04-06 09:00' }
];

// Populate recent activity table
function populateRecentActivity() {
    const tableBody = document.getElementById('recent-activity-table');
    recentActivity.forEach(activity => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${activity.input}</td>
            <td>${activity.type}</td>
            <td>${activity.result}</td>
            <td>${activity.confidence}</td>
            <td>${activity.time}</td>
        `;
        tableBody.appendChild(row);
    });
}

// Quick scan button logic
const quickScanButton = document.getElementById('quick-scan-button');
quickScanButton.addEventListener('click', () => {
    const input = document.getElementById('quick-scan-input').value;
    if (!input) {
        alert('Please enter a URL or message to scan.');
        return;
    }

    // Simulate scanning process
    alert(`Scanning: ${input}`);
    // TODO: Integrate with backend API
});

// Initialize dashboard
populateStats();
populateRecentActivity();

// URL Scanner Logic
const scanUrlButton = document.getElementById('scan-url-button');
scanUrlButton.addEventListener('click', async () => {
    const urlInput = document.getElementById('url-input').value;
    const votingType = document.getElementById('voting-type').value;

    if (!urlInput) {
        alert('Please enter a URL to scan.');
        return;
    }

    // Show loading spinner (to be implemented)

    try {
        const response = await fetch(`/predict-${votingType}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: urlInput })
        });

        const result = await response.json();

        // Update result card
        document.getElementById('url-result').classList.remove('hidden');
        document.getElementById('url-status').querySelector('span').textContent = result.status;
        document.getElementById('url-confidence').querySelector('span').textContent = `${result.confidence}%`;

        // Update analysis panel
        document.getElementById('url-analysis').classList.remove('hidden');
        document.getElementById('url-length').textContent = result.length;
        document.getElementById('url-numbers').textContent = result.containsNumbers ? 'Yes' : 'No';
        document.getElementById('url-words').textContent = result.suspiciousWords.join(', ');
    } catch (error) {
        console.error('Error scanning URL:', error);
        alert('An error occurred while scanning the URL.');
    }

    // Hide loading spinner (to be implemented)
});

// Message Analyzer Logic
const analyzeMessageButton = document.getElementById('analyze-message-button');
analyzeMessageButton.addEventListener('click', async () => {
    const messageInput = document.getElementById('message-input').value;

    if (!messageInput) {
        alert('Please enter a message to analyze.');
        return;
    }

    // Show loading spinner (to be implemented)

    try {
        const response = await fetch('/predict-message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: messageInput })
        });

        const result = await response.json();

        // Update result card
        document.getElementById('message-result').classList.remove('hidden');
        document.getElementById('message-status').querySelector('span').textContent = result.status;
        document.getElementById('message-confidence').querySelector('span').textContent = `${result.confidence}%`;

        // Update analysis panel
        document.getElementById('message-analysis').classList.remove('hidden');
        document.getElementById('message-words').textContent = result.suspiciousWords.join(', ');
    } catch (error) {
        console.error('Error analyzing message:', error);
        alert('An error occurred while analyzing the message.');
    }

    // Hide loading spinner (to be implemented)
});