function FileList(containerId) {
    const container = document.getElementById(containerId);
    const selectedFiles = new Set();
    let onSelectionChange = null;

    function setSelectionChangeHandler(handler) {
        onSelectionChange = handler;
    }

    function getSelectedFiles() {
        return Array.from(selectedFiles);
    }

    async function loadFileStructure() {
        try {
            const response = await fetch('/api/files');
            const files = await response.json();
            
            container.querySelector('tbody').innerHTML = '';
            files.sort((a, b) => a.path.localeCompare(b.path));
            
            files.forEach(file => renderFileRow(file));
        } catch (error) {
            container.querySelector('tbody').innerHTML = 
                `<tr><td colspan="6" class="error">Error loading files: ${error.message}</td></tr>`;
        }
    }

    function renderFileRow(file) {
        const tbody = container.querySelector('tbody');
        const row = document.createElement('tr');
        row.className = 'file-row';
        
        // Checkbox cell
        row.appendChild(createCheckboxCell(file));
        
        // Expand button cell
        row.appendChild(createExpandButtonCell(file, row));
        
        // File name and status
        row.appendChild(createFileNameCell(file));
        
        // Metadata cells
        row.appendChild(createCell(new Date(file.mtime * 1000).toLocaleString()));
        row.appendChild(createCell(`${(file.size / 1024).toFixed(2)} KB`));
        row.appendChild(createCell(file.tokens.toString()));
        
        tbody.appendChild(row);

        // Add diff row if diff exists
        if (file.diff) {
            const diffRow = createDiffRow(file.diff);
            diffRow.style.display = 'none'; // Ensure the diff row is hidden initially
            tbody.appendChild(diffRow);
        }
    }

    function createCheckboxCell(file) {
        const cell = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = selectedFiles.has(file.path);
        checkbox.addEventListener('change', (e) => {
            e.stopPropagation();
            if (checkbox.checked) {
                selectedFiles.add(file.path);
            } else {
                selectedFiles.delete(file.path);
            }
            if (onSelectionChange) {
                onSelectionChange(Array.from(selectedFiles));
            }
        });
        cell.appendChild(checkbox);
        return cell;
    }

    function createExpandButtonCell(file, row) {
        const cell = document.createElement('td');
        if (file.diff) {
            const button = document.createElement('button');
            button.className = 'expand-button';
            button.innerHTML = '
                \\u25b6';
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleDiff(file.path, row);
            });
            cell.appendChild(button);
        }
        return cell;
    }

    function createFileNameCell(file) {
        const cell = document.createElement('td');
        cell.innerHTML = file.path;
        if (file.git_status !== 'unmodified') {
            const badge = document.createElement('span');
            badge.className = `status-badge status-${file.git_status}`;
            badge.textContent = file.git_status;
            cell.appendChild(badge);
        }
        return cell;
    }

    function createCell(text) {
        const cell = document.createElement('td');
        cell.textContent = text;
        return cell;
    }

    function createDiffRow(diff) {
        const row = document.createElement('tr');
        row.className = 'diff-row';
        const cell = document.createElement('td');
        cell.colSpan = 6;
        const content = document.createElement('div');
        content.className = 'diff-view';
        content.innerHTML = formatDiff(diff);
        cell.appendChild(content);
        row.appendChild(cell);
        return row;
    }

    function formatDiff(diff) {
        if (!diff) return '';
        
        const lines = diff.split('\n');
        let html = '<div class="diff-content">';
        
        lines.forEach((line, index) => {
            let className = 'diff-line';
            if (line.startsWith('+')) {
                className += ' addition';
            } else if (line.startsWith('-')) {
                className += ' deletion';
            } else if (line.startsWith('@')) {
                className += ' info';
            }
            
            html += `
                <div class="${className}">
                    <span class="diff-line-number">${index + 1}</span>
                    <span class="diff-line-content">${escapeHtml(line)}</span>
                </div>`;
        });
        
        html += '</div>';
        return html;
    }

    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function toggleDiff(filePath, row) {
        const diffRow = row.nextElementSibling;
        if (diffRow && diffRow.classList.contains('diff-row')) {
            const diffView = diffRow.querySelector('.diff-view');
            const expandButton = row.querySelector('.expand-button');
            
            if (diffView.classList.contains('expanded')) {
                diffView.classList.remove('expanded');
                expandButton.innerHTML = '
                    \\u25b6';
            } else {
                diffView.classList.add('expanded');
                expandButton.innerHTML = '
                    \\u25bc';
            }
        }
    }

    return {
        load: loadFileStructure,
        getSelectedFiles,
        setSelectionChangeHandler
    };
}
