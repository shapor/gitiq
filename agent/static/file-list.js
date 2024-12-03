function FileList(containerId) {
    const container = document.getElementById(containerId);
    const selectedFiles = new Set();
    let filesData = [];
    let currentSortKey = 'path';
    let currentSortOrder = 'asc';
    let onSelectionChange = null;

    const selectAllCheckbox = document.getElementById('selectAll');
    selectAllCheckbox.addEventListener('change', handleSelectAll);

    function handleSelectAll() {
        const checkboxes = container.querySelectorAll('tbody input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = selectAllCheckbox.checked;
            updateSelectedFiles(checkbox);
        });
        updateTokenCount();
        notifySelectionChange();
        updateExtensionCheckboxes();
    }

    function handleExtensionChange(event) {
        const extension = event.target.getAttribute('data-extension');
        const isChecked = event.target.checked;
        const checkboxes = container.querySelectorAll(`tbody input[type="checkbox"][data-extension="${extension}"]`);
        checkboxes.forEach(checkbox => {
            checkbox.checked = isChecked;
            updateSelectedFiles(checkbox);
        });
        updateTokenCount();
        notifySelectionChange();
        updateSelectAllCheckbox();
    }

    function updateSelectedFiles(checkbox) {
        const filePath = checkbox.dataset.filePath;
        if (checkbox.checked) {
            selectedFiles.add(filePath);
        } else {
            selectedFiles.delete(filePath);
        }
    }

    function notifySelectionChange() {
        if (onSelectionChange) {
            onSelectionChange(Array.from(selectedFiles));
        }
    }

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

    function updateExtensionCheckboxes() {
        const extensionContainer = document.getElementById('extensionFilters');
        const extensionCheckboxes = extensionContainer.querySelectorAll('input[type="checkbox"]');
        
        extensionCheckboxes.forEach(extCheckbox => {
            const extension = extCheckbox.dataset.extension;
            const fileCheckboxes = container.querySelectorAll(`tbody input[type="checkbox"][data-extension="${extension}"]`);
            const checkedCount = Array.from(fileCheckboxes).filter(cb => cb.checked).length;
            
            if (checkedCount === 0) {
                extCheckbox.checked = false;
                extCheckbox.indeterminate = false;
            } else if (checkedCount === fileCheckboxes.length) {
                extCheckbox.checked = true;
                extCheckbox.indeterminate = false;
            } else {
                extCheckbox.checked = false;
                extCheckbox.indeterminate = true;
            }
        });
    }

    async function loadFileStructure() {
        try {
            const response = await fetch('/api/files');
            filesData = await response.json();
            renderFileTable();
            renderExtensionCheckboxes();
        } catch (error) {
            container.querySelector('tbody').innerHTML = 
                `<tr><td colspan="6" class="error">Error loading files: ${error.message}</td></tr>`;
        }
    }

    function renderExtensionCheckboxes() {
        const extensionContainer = document.getElementById('extensionFilters');
        extensionContainer.innerHTML = 'Select by extension: '; // Clear existing checkboxes and add label

        const uniqueExtensions = [...new Set(filesData.map(file => getFileExtension(file.path)))]
            .filter(ext => ext.length <= 4)
            .sort();
        uniqueExtensions.forEach(ext => {
            const label = document.createElement('label');
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.classList.add('extension-checkbox');
            checkbox.dataset.extension = ext;
            checkbox.checked = false;
            checkbox.addEventListener('change', handleExtensionChange);
            label.appendChild(checkbox);
            label.appendChild(document.createTextNode(ext));
            extensionContainer.appendChild(label);
        });
    }

    function sortFiles(files) {
        return files.slice().sort((a, b) => {
            let valA = a[currentSortKey];
            let valB = b[currentSortKey];
            if (typeof valA === 'string') valA = valA.toLowerCase();
            if (typeof valB === 'string') valB = valB.toLowerCase();
            if (valA < valB) return currentSortOrder === 'asc' ? -1 : 1;
            if (valA > valB) return currentSortOrder === 'asc' ? 1 : -1;
            return 0;
        });
    }

    function renderFileTable() {
        const tbody = container.querySelector('tbody');
        tbody.innerHTML = '';
        const sortedFiles = sortFiles(filesData);
        sortedFiles.forEach(file => renderFileRow(file, tbody));
    }

    function renderFileRow(file, tbody) {
        const row = document.createElement('tr');
        row.className = 'file-row';
        
        row.appendChild(createCheckboxCell(file));
        row.appendChild(createExpandButtonCell(file, row));
        row.appendChild(createFileNameCell(file));
        row.appendChild(createCell(getRelativeTime(file.mtime)));
        row.appendChild(createCell(`${file.size} bytes`));
        row.appendChild(createCell(file.tokens.toString()));
        
        tbody.appendChild(row);

        if (file.diff) {
            const diffRow = createDiffRow(file.diff);
            diffRow.style.display = 'none';
            tbody.appendChild(diffRow);
        }
    }

    function getRelativeTime(unixTimestamp) {
        const now = Date.now() / 1000;
        const diffSeconds = Math.floor(now - unixTimestamp);

        const units = [
            { name: 'year', duration: 365 * 24 * 60 * 60 },
            { name: 'month', duration: 30 * 24 * 60 * 60 },
            { name: 'day', duration: 24 * 60 * 60 },
            { name: 'hour', duration: 60 * 60 },
            { name: 'minute', duration: 60 },
            { name: 'second', duration: 1 }
        ];

        for (let unit of units) {
            const count = Math.floor(diffSeconds / unit.duration);
            if (count >= 1) {
                return `${count} ${unit.name}${count > 1 ? 's' : ''} ago`;
            }
        }
        return 'just now';
    }

    function createCheckboxCell(file) {
        const cell = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = selectedFiles.has(file.path);
        checkbox.dataset.filePath = file.path;
        checkbox.dataset.extension = getFileExtension(file.path);
        checkbox.addEventListener('change', handleCheckboxChange);
        cell.appendChild(checkbox);
        return cell;
    }

    function getFileExtension(filePath) {
        return filePath.split('.').pop().toLowerCase();
    }

    function handleCheckboxChange(e) {
        e.stopPropagation();
        updateSelectedFiles(e.target);
        updateTokenCount();
        notifySelectionChange();
        updateSelectAllCheckbox();
        updateExtensionCheckboxes();
    }

    function updateSelectAllCheckbox() {
        const totalCheckboxes = container.querySelectorAll('tbody input[type="checkbox"]').length;
        const checkedCheckboxes = container.querySelectorAll('tbody input[type="checkbox"]:checked').length;
        
        if (checkedCheckboxes === 0) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        } else if (checkedCheckboxes === totalCheckboxes) {
            selectAllCheckbox.checked = true;
            selectAllCheckbox.indeterminate = false;
        } else {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = true;
        }
    }

    function createExpandButtonCell(file, row) {
        const cell = document.createElement('td');
        if (file.diff) {
            const button = document.createElement('button');
            button.className = 'expand-button';
            button.innerHTML = '\u25b6';
            button.addEventListener('click', () => toggleDiff(file.path, row));
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
        header.addEventListener('click', () => {
            const sortKey = header.dataset.sortKey;
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
