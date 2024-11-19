// Initialize file list
const fileList = new FileList('fileList');

// State management
let isProcessing = false;

// DOM elements
const repoStatus = document.getElementById('repoStatus');
const modelSelect = document.getElementById('modelSelect');
const promptInput = document.getElementById('promptInput');
const submitBtn = document.getElementById('submitBtn');
const submitMessage = document.getElementById('submitMessage');
const submitStatus = document.getElementById('submitStatus');
const loading = document.getElementById('loading');
const currentStage = document.getElementById('currentStage');
const stageTiming = document.getElementById('stageTiming');
const logSection = document.getElementById('logSection');

function setStatusSpinner() {
    submitStatus.innerHTML = '<span class="spinner"></span>';
    submitStatus.classList.add('visible');
}

function setStatusSuccess() {
    submitStatus.innerHTML = '<span class="success">&#10003;</span>';
    submitStatus.classList.add('visible');
}

function setStatusError() {
    submitStatus.innerHTML = '<span class="error">&#10007;</span>';
    submitStatus.classList.add('visible');
}

function clearStatus() {
    submitStatus.classList.remove('visible');
    setTimeout(() => {
        submitStatus.innerHTML = '';
    }, 300); // Match the CSS transition duration
}

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
    const timestamp = new Date().toLocaleTimeString();
    entry.innerHTML = `<span class="log-timestamp">[${timestamp}]</span> ${message}`;
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
    const selectedFiles = fileList.getSelectedFiles();
    const promptText = promptInput.value.trim();
    submitBtn.disabled = isProcessing || selectedFiles.length === 0 || !promptText;

    if (submitBtn.disabled && selectedFiles.length === 0) {
        submitMessage.textContent = 'Please select files below.';
    } else {
        submitMessage.textContent = '';
    }
}

async function generatePR() {
    if (isProcessing) return;
    
    isProcessing = true;
    submitBtn.disabled = true;
    setStatusSpinner();
    
    const body = {
        prompt: promptInput.value,
        selected_files: fileList.getSelectedFiles(),
        model: modelSelect.value
    };

    // Get the number of files
    const numFiles = body.selected_files.length;

    // Get the token count from the DOM
    const tokenCountSpan = document.getElementById('tokenCount');
    const tokenText = tokenCountSpan.textContent; // e.g., "(123 tokens selected)"
    const matches = tokenText.match(/(\d+) tokens selected/);
    const numTokens = matches ? parseInt(matches[1], 10) : 0;

    // Get model name
    const modelName = modelSelect.value;

    // Add log entry
    addLogEntry(`A new request was dispatched for ${numFiles} files (${numTokens} tokens) to model ${modelName}`, 'info');
    
    // Remove this line to keep existing log entries
    // logSection.innerHTML = '';
    currentStage.textContent = '';
    stageTiming.textContent = '';
    
    try {
        const response = await fetch('/api/pr/create/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const {value, done} = await reader.read();
            if (done) break;

            buffer += decoder.decode(value);

            let boundary = buffer.indexOf('\n');
            while (boundary !== -1) {
                let line = buffer.slice(0, boundary).trim();
                buffer = buffer.slice(boundary + 1);

                if (line) {
                    // Handle lines that start with 'data: '
                    if (line.startsWith('data: ')) {
                        line = line.slice(6);
                    }
                    try {
                        const event = JSON.parse(line);

                        if (event.timing) {
                            stageTiming.textContent = formatStageTime(event.timing);
                        }

                        if (event.stage) {
                            addLogEntry(`${event.stage}: ${event.message}`, event.stage);
                            if (event.llm_stats) {
                                const stats = event.llm_stats;
                                const statsMessage = `LLM Stats - Total Tokens: ${stats.total_tokens}, Prompt Tokens: ${stats.prompt_tokens}, Completion Tokens: ${stats.completion_tokens}, Cost: $${stats.cost.toFixed(4)}`;
                                addLogEntry(statsMessage, 'stats');
                            }
                        } else if (event.type) {
                            switch (event.type) {
                                case 'info':
                                    currentStage.textContent = event.message;
                                    addLogEntry(event.message, 'info');
                                    if (event.llm_stats) {
                                        const stats = event.llm_stats;
                                        const statsMessage = `LLM Stats - Total Tokens: ${stats.total_tokens}, Prompt Tokens: ${stats.prompt_tokens}, Completion Tokens: ${stats.completion_tokens}, Cost: $${stats.cost.toFixed(4)}`;
                                        addLogEntry(statsMessage, 'stats');
                                    }
                                    break;

                                case 'error':
                                    addLogEntry(event.message, 'error');
                                    setStatusError();
                                    break;

                                case 'complete':
                                    const prUrl = event.pr_url;
                                    const message = prUrl.startsWith('local://') ?
                                        `Local branch created: ${prUrl.replace('local://', '')}` :
                                        `PR created: ${prUrl}`;
                                    addLogEntry(message, 'success');

                                    if (event.pr_description) {
                                        addLogEntry('PR Description:', 'info');
                                        addLogEntry(event.pr_description, 'pr-description');
                                    }

                                    if (event.timings) {
                                        addLogEntry('Stage Timings:', 'info');
                                        Object.entries(event.timings).forEach(([stage, time]) => {
                                            addLogEntry(`${stage}: ${formatStageTime(time)}`, 'info');
                                        });
                                    }

                                    if (event.llm_stats) {
                                        const stats = event.llm_stats;
                                        const statsMessage = `Total Tokens: ${stats.total_tokens}, Cost: $${stats.cost.toFixed(4)}`;
                                        addLogEntry(statsMessage, 'stats');
                                    }
                                    setStatusSuccess();
                                    break;

                                default:
                                    console.warn('Unknown event type', event);
                                    break;
                            }
                        } else {
                            console.warn('Unknown event format', event);
                        }
                    } catch (error) {
                        console.error('Failed to parse JSON:', line, error);
                    }
                }

                boundary = buffer.indexOf('\n');
            }
        }
    } catch (error) {
        addLogEntry(`Error: ${error.message}`, 'error');
        setStatusError();
    } finally {
        isProcessing = false;
        currentStage.textContent = '';
        stageTiming.textContent = '';
        updateSubmitButton();
        await fileList.load();
    }
}

// Event listeners
promptInput.addEventListener('input', function() {
    clearStatus();
    updateSubmitButton();
});

fileList.setSelectionChangeHandler(function() {
    clearStatus();
    updateSubmitButton();
});

submitBtn.addEventListener('click', generatePR);

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