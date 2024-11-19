function FileList(containerId) {
    const container = document.getElementById(containerId);
    const selectedFiles = new Set();
    let filesData = [];
    let currentSortKey = '';
    let currentSortOrder = 'asc';
    let onSelectionChange = null;

    const selectAllCheckbox = document.getElementById('selectAll');
    selectAllCheckbox.addEventListener('change', (e) => {
        const checkboxes = container.querySelectorAll('tbody input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = selectAllCheckbox.checked;
            const filePath = checkbox.dataset.filePath;
            if (checkbox.checked) {
                selectedFiles.add(filePath);
            } else {
                selectedFiles.delete(filePath);
            }
        });
        updateTokenCount();
        if (onSelectionChange) {
            onSelectionChange(Array.from(selectedFiles));
        }
    });

    function setSelectionChangeHandler(handler) {
        onSelectionChange = handler;
    }

    function getSelectedFiles() {
        return Array.from(selectedFiles);
    }

    function updateTokenCount() {
        const tokenSum = Array.from(container.querySelectorAll('tbody input[type="checkbox"]:checked'))
            .reduce((sum, checkbox) => {
                const row = checkbox.closest('tr');
                const tokenCell = row.querySelector('td:last-child');
                return sum + parseInt(tokenCell.textContent || 0);
            }, 0);
        
        const tokenCounter = document.getElementById('tokenCount');
        tokenCounter.textContent = `(${tokenSum} tokens selected)`;
    }

    async function loadFileStructure() {
        try {
            const response = await fetch('/api/files');
            const files = await response.json();
            filesData = files;
            renderFileTable();
        } catch (error) {
            container.querySelector('tbody').innerHTML = 
                `<tr><td colspan="6" class="error">Error loading files: ${error.message}</td></tr>`;
        }
    }

    function renderFileTable() {
        const tbody = container.querySelector('tbody');
        tbody.innerHTML = '';
        let sortedFiles = filesData.slice();
        if (currentSortKey) {
            sortedFiles.sort((a, b) => {
                let valA = a[currentSortKey];
                let valB = b[currentSortKey];
                if (typeof valA === 'string') valA = valA.toLowerCase();
                if (typeof valB === 'string') valB = valB.toLowerCase();
                if (valA < valB) return currentSortOrder === 'asc' ? -1 : 1;
                if (valA > valB) return currentSortOrder === 'asc' ? 1 : -1;
                return 0;
            });
        }
        sortedFiles.forEach(file => renderFileRow(file));
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
        row.appendChild(createCell(`${file.size} bytes`));
        row.appendChild(createCell(file.tokens.toString()));
        
        tbody.appendChild(row);

        // Add diff row if diff exists
        if (file.diff) {
            const diffRow = createDiffRow(file.diff);
            diffRow.style.display = 'none';
            tbody.appendChild(diffRow);
        }
    }

    function createCheckboxCell(file) {
        const cell = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = selectedFiles.has(file.path);
        checkbox.dataset.filePath = file.path;
        checkbox.addEventListener('change', (e) => {
            e.stopPropagation();
            if (checkbox.checked) {
                selectedFiles.add(file.path);
            } else {
                selectedFiles.delete(file.path);
            }
            updateTokenCount();
            if (onSelectionChange) {
                onSelectionChange(Array.from(selectedFiles));
            }
            const totalCheckboxes = container.querySelectorAll('tbody input[type="checkbox"]').length;
            const checkedCheckboxes = container.querySelectorAll('tbody input[type="checkbox"]:checked').length;
            selectAllCheckbox.checked = (totalCheckboxes === checkedCheckboxes);
        });
        cell.appendChild(checkbox);
        return cell;
    }

    function createExpandButtonCell(file, row) {
        const cell = document.createElement('td');
        if (file.diff) {
            const button = document.createElement('button');
            button.className = 'expand-button';
            button.innerHTML = '\u25b6';
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
                expandButton.innerHTML = '\u25b6';
                diffRow.style.display = 'none';
            } else {
                diffView.classList.add('expanded');
                expandButton.innerHTML = '\u25bc';
                diffRow.style.display = 'table-row';
            }
        }
    }

    const headerCells = container.querySelectorAll('thead th.sortable');
    headerCells.forEach(header => {
        header.addEventListener('click', function() {
            const sortKey = this.dataset.sortKey;
            if (currentSortKey === sortKey) {
                currentSortOrder = (currentSortOrder === 'asc') ? 'desc' : 'asc';
            } else {
                currentSortKey = sortKey;
                currentSortOrder = 'asc';
            }
            renderFileTable();
        });
    });

    return {
        load: loadFileStructure,
        getSelectedFiles,
        setSelectionChangeHandler
    };
}
