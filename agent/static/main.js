// Initialize file list
const fileList = new FileList('fileList');

// State management
let isProcessing = false;

// DOM elements
const repoStatus = document.getElementById('repoStatus');
const modelSelect = document.getElementById('modelSelect');
const promptInput = document.getElementById('promptInput');
const submitBtn = document.getElementById('submitBtn');
const loading = document.getElementById('loading');
const currentStage = document.getElementById('currentStage');
const stageTiming = document.getElementById('stageTiming');
const logSection = document.getElementById('logSection');

async function checkRepoStatus() {
    try {
        const response = await fetch('/api/repo/status');
        const status = await response.json();

        if (!status.is_git_repo) {
            repoStatus.textContent = 'Error: Not a Git repository';
            repoStatus.classList.add('status-error');
            submitBtn.disabled = true;
            return false;
        }

        repoStatus.textContent = `Repository: ${status.current_branch}`;
        repoStatus.classList.remove('status-error');
        return true;
    } catch (error) {
        repoStatus.textContent = `Error: ${error.message}`;
        repoStatus.classList.add('status-error');
        submitBtn.disabled = true;
        return false;
    }
}

async function loadModels() {
    try {
        const response = await fetch('/api/models');
        const models = await response.json();
        
        modelSelect.innerHTML = models.map(model => 
            `<option value="${model}">${model}</option>`
        ).join('');
    } catch (error) {
        modelSelect.innerHTML = '<option value="gpt-4-turbo-preview">GPT-4 Turbo</option>';
    }
}

function addLogEntry(message, type = 'info') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = message;
    logSection.appendChild(entry);
    // Force a reflow to ensure the 'visible' class transition works
    entry.offsetHeight;
    entry.classList.add('visible');
    logSection.scrollTop = logSection.scrollHeight;
}

function formatStageTime(ms) {
    return ms ? `(${(ms / 1000).toFixed(1)}s)` : '';
}

function updateSubmitButton() {
    submitBtn.disabled = isProcessing || 
        fileList.getSelectedFiles().length === 0 || 
        !promptInput.value.trim();
}

async function generatePR() {
    if (isProcessing) return;
    
    isProcessing = true;
    submitBtn.disabled = true;
    loading.classList.add('visible');
    logSection.innerHTML = '';
    currentStage.textContent = '';
    stageTiming.textContent = '';
    
    const body = {
        prompt: promptInput.value,
        selected_files: fileList.getSelectedFiles(),
        model: modelSelect.value
    };

    try {
        const response = await fetch('/api/pr/create/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const {value, done} = await reader.read();
            if (done) break;
            
            const events = decoder.decode(value)
                .split('\n\n')
                .filter(line => line.startsWith('data: '))
                .map(line => JSON.parse(line.slice(6)));

            for (const event of events) {
                if (event.timing) {
                    stageTiming.textContent = formatStageTime(event.timing);
                }

                switch (event.type) {
                    case 'info':
                        currentStage.textContent = event.message;
                        addLogEntry(event.message);
                        if (event.stats) {
                            addLogEntry(`Stats: ${JSON.stringify(event.stats)}`, 'stats');
                        }
                        break;

                    case 'error':
                        addLogEntry(event.message, 'error');
                        break;

                    case 'complete':
                        const prUrl = event.pr_url;
                        const message = prUrl.startsWith('local://') ?
                            `Local branch created: ${prUrl.replace('local://', '')}` :
                            `PR created: ${prUrl}`;
                        addLogEntry(message, 'success');
                        
                        if (event.timings) {
                            addLogEntry('Stage Timings:', 'info');
                            Object.entries(event.timings).forEach(([stage, time]) => {
                                addLogEntry(`${stage}: ${formatStageTime(time)}`, 'info');
                            });
                        }
                        break;
                }
            }
        }
    } catch (error) {
        addLogEntry(`Error: ${error.message}`, 'error');
    } finally {
        isProcessing = false;
        loading.classList.remove('visible');
        currentStage.textContent = '';
        stageTiming.textContent = '';
        updateSubmitButton();
        await fileList.load();
    }
}

// Event listeners
promptInput.addEventListener('input', updateSubmitButton);
submitBtn.addEventListener('click', generatePR);
fileList.setSelectionChangeHandler(updateSubmitButton);

// Initialize
async function initialize() {
    const repoOk = await checkRepoStatus();
    if (repoOk) {
        await Promise.all([
            fileList.load(),
            loadModels()
        ]);
    }
    // Add a test log entry to ensure the log section is working
    addLogEntry('GitIQ initialized successfully', 'info');
}

initialize();