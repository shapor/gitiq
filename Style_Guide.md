# GitIQ Style Guide

## Core Philosophy: KEEP IT SIMPLE!

Our primary goal is to maintain a codebase that is easy to understand, modify, and debug. We deliberately avoid complexity and favor straightforward solutions over clever ones.

## Technology Stack

### Backend
- Pure Python with Flask
- No ORM layers or database abstractions
- Standard library modules preferred over third-party packages
- Only essential dependencies allowed:
  - Flask (for HTTP server)
  - GitPython (for git operations)
  - Required LLM API client

### Frontend
- Pure HTML and JavaScript
- No frameworks or libraries (not even jQuery)
- No bundlers, transpilers, or build tools
- No CSS preprocessors
- No package managers (no npm/yarn)

## Coding Standards

### General Principles
- Favor readability over brevity
- Write self-documenting code
- Single responsibility per function/module
- Avoid premature optimization
- No clever one-liners that sacrifice clarity
- No classes - use pure functions and simple data structures

### Python Guidelines
- Use Python 3.8+ features but avoid bleeding-edge syntax
- Follow PEP 8 naming conventions:
  - `snake_case` for functions and variables
  - `UPPER_CASE` for constants
- Maximum line length: 88 characters (black's default)
- Clear docstrings for public functions
- Type hints only where they improve clarity
- No object-oriented programming - use pure functions
- No decorators except for Flask routes
- Store related data in dictionaries or named tuples

Example Python:
```python
def create_feature_branch(prompt: str) -> str:
    """Create a new git branch for the AI-generated changes.
    
    Args:
        prompt: The user's natural language prompt
        
    Returns:
        The name of the created branch
    """
    # Simple, direct implementation
    branch_name = f"GitIQ-{sanitize_branch_name(prompt)}"
    repo = git.Repo(".")
    new_branch = repo.create_head(branch_name)
    new_branch.checkout()
    return branch_name

def get_commit_info(prompt: str, files_modified: list[str]) -> dict:
    """Build commit information dictionary.
    
    Args:
        prompt: Original user prompt
        files_modified: List of modified file paths
        
    Returns:
        Dictionary with commit metadata
    """
    return {
        'prompt': prompt,
        'files': files_modified,
        'model': 'gpt-4-turbo-preview',
        'timestamp': datetime.now().isoformat()
    }
```

### JavaScript Guidelines
- Use vanilla ES6+ features but avoid experimental syntax
- No transpilation or polyfills
- Clear function and variable names
- Prefer `const` and `let` over `var`
- Use simple DOM manipulation instead of virtual DOM
- Avoid complex state management
- Maximum 2 levels of callback nesting
- Use async/await for asynchronous operations
- Store state in simple objects, not classes

Example JavaScript:
```javascript
async function submitPrompt() {
    const promptText = document.getElementById('prompt-input').value;
    const selectedFiles = getSelectedFiles();
    
    try {
        showLoadingState();
        const response = await fetch('/api/create-pr', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                prompt: promptText,
                files: selectedFiles
            })
        });
        
        const result = await response.json();
        showSuccess(result.prUrl);
    } catch (error) {
        showError(error.message);
    }
}

function getSelectedFiles() {
    const checkboxes = document.querySelectorAll('.file-selector__checkbox:checked');
    return Array.from(checkboxes).map(checkbox => checkbox.value);
}
```

### HTML/CSS Guidelines
- Semantic HTML5 elements
- No CSS frameworks or resets
- Simple, flat CSS selectors
- Avoid deep nesting of elements
- Use CSS Grid and Flexbox for layouts
- No CSS-in-JS or styled components
- Minimal media queries
- BEM naming convention for CSS classes

Example HTML/CSS:
```html
<div class="file-selector">
    <h2 class="file-selector__title">Select Files</h2>
    <ul class="file-selector__list">
        <li class="file-selector__item">
            <input type="checkbox" id="file1" class="file-selector__checkbox">
            <label for="file1" class="file-selector__label">auth.py</label>
        </li>
    </ul>
</div>

<style>
.file-selector {
    margin: 20px;
    padding: 15px;
    border: 1px solid #ddd;
}

.file-selector__list {
    list-style: none;
    padding: 0;
}

.file-selector__item {
    margin: 5px 0;
    display: flex;
    align-items: center;
}
</style>
```

## Project Structure
```
gitiq/
├── server/
│   ├── app.py          # Flask application
│   ├── git_ops.py      # Git operations
│   └── llm_client.py   # LLM API client
├── static/
│   ├── style.css       # Global styles
│   └── main.js         # Frontend JavaScript
└── templates/
    └── index.html      # Single page application
```

## Forbidden Practices
- No object-oriented programming or classes
- No code generation tools or scaffolding
- No build processes or compilation steps
- No CSS preprocessors or postprocessors
- No state management libraries
- No frontend frameworks (React, Vue, Angular, etc.)
- No backend frameworks except Flask
- No ORMs or database abstractions
- No template engines except Flask's default
- No component libraries or UI kits
- No utility libraries (lodash, underscore, etc.)
