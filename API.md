# GitIQ API Specification

## Endpoints

### Get Repository Status
```
GET /api/repo/status
```

Returns the repository's Git configuration status.

**Response**
```json
{
    "is_git_repo": true,
    "current_branch": "main"
}
```

### Get File Structure
```
GET /api/files
```

Returns a list of files in the repository along with their metadata.

**Response**
```json
[
    {
        "path": "src/main.py",
        "size": 1024,
        "mtime": 1699974400,
        "is_binary": false,
        "lines": 45,
        "tokens": 320,
        "git_status": "unmodified",
        "diff": null
    },
    {
        "path": "src/auth.py",
        "size": 2048,
        "mtime": 1699974500,
        "is_binary": false,
        "lines": 128,
        "tokens": 876,
        "git_status": "modified",
        "diff": "@@ -1,7 +1,7 @@\n import json\n\n-def auth_user():\n+def auth_user(token=null):\n     user = get_user()\n     if not user:\n         return null\n     return user.id"
    },
    {
        "path": "tests/test_main.py",
        "size": 512,
        "mtime": 1699974600,
        "is_binary": false,
        "lines": 32,
        "tokens": 245,
        "git_status": "untracked",
        "diff": null
    }
]
```

The `git_status` field can be one of:
- `unmodified`: No changes
- `modified`: File has local changes
- `untracked`: New file, not yet tracked
- `deleted`: File was deleted
- `renamed`: File was renamed
- `ignored`: File is in `.gitignore`

The `diff` field contains:
- Standard unified diff format (3 lines of context) if the file is modified
- `null` for unmodified, untracked, or binary files

### Create PR with Status Stream
```
POST /api/pr/create/stream
```

Creates a new change in a local branch or a GitHub Pull Request and streams status updates.

**Parameters**
| Name           | Type     | Required | Description                                                                 |
|----------------|----------|----------|-----------------------------------------------------------------------------|
| `prompt`       | string   | Yes      | Description of desired changes                                              |
| `selected_files`| string[] | Yes      | Array of file paths to modify                                               |
| `context_files` | string[] | No       | Array of file paths providing additional context                            |
| `model`        | string   | No       | LLM model to use (default: system configured)                              |
| `change_type`  | string   | No       | Type of change: `local` for local branch or `github` for PR (default based on system configuration)

**Example Request**
```json
{
    "prompt": "Update auth system to use JWT tokens instead of cookies",
    "selected_files": ["src/auth.py", "src/user_model.py"],
    "context_files": ["docs/auth_requirements.md"],
    "model": "gpt-4-turbo-preview",
    "change_type": "github"
}
```

**Event Stream Formats**

- **Basic status update:**
  ```json
  {
      "type": "info",
      "message": "Creating branch GitIQ-auth-update..."
  }
  ```

- **Status update with metrics:**
  ```json
  {
      "type": "info",
      "message": "Generating changes using GPT-4...",
      "stats": {
          "prompt_tokens": 1420,
          "completion_tokens": 0,
          "total_cost": 0.02,
          "elapsed_time": 1.2,
          "files_modified": 0,
          "lines_changed": 0
      }
  }
  ```

- **Completion:**
  ```json
  {
      "type": "complete",
      "message": "PR created successfully",
      "stats": {
          "prompt_tokens": 1420,
          "completion_tokens": 843,
          "total_cost": 0.05,
          "elapsed_time": 4.3,
          "files_modified": 2,
          "lines_changed": 156
      },
      "pr_url": "https://github.com/org/repo/pull/123"
  }
  ```

- **Completion for local branch:**
  ```json
  {
      "type": "complete",
      "message": "Local branch created successfully",
      "stats": {
          "prompt_tokens": 1420,
          "completion_tokens": 843,
          "total_cost": 0.05,
          "elapsed_time": 4.3,
          "files_modified": 2,
          "lines_changed": 156
      },
      "pr_url": "local://GitIQ-auth-update"
  }
  ```

- **Error:**
  ```json
  {
      "type": "error",
      "message": "Failed to generate changes: API error"
  }
  ```
