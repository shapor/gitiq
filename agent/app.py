"""app.py - Main Flask application for GitIQ"""
import os
import json
import time
import logging
import re
from flask import Flask, request, jsonify, Response, send_from_directory
from git import Repo, InvalidGitRepositoryError, Actor

from llm_integration import load_llm_config, list_models, count_tokens
from stream_events import StreamProcessor
from github_integration import create_github_pr, process_pr_comments

def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - level=%(levelname)s - %(message)s"))
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger

logger = setup_logging()

# Initialize Flask app
app = Flask(__name__, static_url_path='', static_folder='static')
app.debug = False

# Load configuration
with open('config.json') as f:
    config = json.load(f)
    git_config = config.get('git', {})
    GIT_BOT = Actor(
        git_config.get('name', 'GitIQ-bot'),
        git_config.get('email', 'gitiq-bot@github.com')
    )
    GITHUB_ENABLED = config.get('github', {}).get('enabled', False)

# Load LLM configuration
load_llm_config('config.json')

# Start PR comment processing if GitHub is enabled
if GITHUB_ENABLED:
    process_pr_comments()

def get_repo_status():
    """Get Git repository status information"""
    try:
        repo = Repo(os.getcwd())
        return {
            "is_git_repo": True,
            "current_branch": repo.active_branch.name
        }
    except InvalidGitRepositoryError:
        return {
            "is_git_repo": False,
            "current_branch": None
        }

def get_file_structure(repo_path="."):
    """Get repository file structure with Git status"""
    try:
        repo = Repo(repo_path)
        tracked_files = set(repo.git.ls_files().splitlines())
        untracked_files = set(repo.git.ls_files('--others', '--exclude-standard').splitlines())
        status = repo.index.diff(None)

        def get_git_status(file_path):
            if file_path in untracked_files:
                return "untracked"
            for diff in status:
                if diff.a_path == file_path:
                    if diff.change_type == "D":
                        return "deleted"
                    elif diff.change_type == "R":
                        return "renamed"
                    else:
                        return "modified"
            return "unmodified"

        result = []
        for file_path in tracked_files | untracked_files:
            try:
                is_binary = False
                lines = 0
                tokens = 0
                diff = None

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        is_binary = '\0' in content
                        if not is_binary:
                            lines = len(content.splitlines())
                            tokens = count_tokens(content)
                except UnicodeDecodeError:
                    is_binary = True

                git_status = get_git_status(file_path)
                if git_status == "modified":
                    try:
                        diff = repo.git.diff(file_path)
                    except Exception:
                        diff = None

                result.append({
                    "path": file_path,
                    "size": os.path.getsize(file_path),
                    "mtime": int(os.path.getmtime(file_path)),
                    "is_binary": is_binary,
                    "lines": lines,
                    "tokens": tokens,
                    "git_status": git_status,
                    "diff": diff
                })
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")

        return result
    except InvalidGitRepositoryError:
        return []

def generate_branch_name():
    """Generate default branch name with timestamp"""
    return f"GitIQ-{int(time.time())}"

def is_valid_branch_name(name):
    """Validate branch name according to Git naming conventions"""
    branch_name_pattern = re.compile(r'^(?!/)(?!.*//)(?!.*/$)[\w\-.\/]+$')
    return bool(branch_name_pattern.match(name)) and len(name) <= 50

def cleanup_failed_operation(repo, original_branch, new_branch_name, change_type):
    """Clean up after failed operation"""
    try:
        if original_branch:
            original_branch.checkout()
        # Only delete local branch if change_type is 'local'
        if new_branch_name and new_branch_name in repo.heads:
            if change_type == 'local':
                repo.delete_head(new_branch_name, force=True)
        # Attempt to delete remote branch if change_type is 'github'
        if change_type == 'github':
            try:
                repo.git.push('origin', '--delete', new_branch_name)
                logger.info(f"Deleted remote branch '{new_branch_name}' from remote 'origin'")
            except Exception as e:
                logger.warning(f"Failed to delete remote branch '{new_branch_name}': {str(e)}")
    except Exception as e:
        logger.error(f"Failed to cleanup: {str(e)}")

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/repo/status')
def repo_status():
    """Get repository status endpoint"""
    return jsonify(get_repo_status())

@app.route('/api/files')
def files():
    """Get file structure endpoint"""
    return jsonify(get_file_structure())

@app.route('/api/models')
def models():
    """Get available LLM models"""
    return jsonify(list_models())

@app.route('/api/pr/create/stream', methods=['POST'])
def create_pr():
    """Create PR with streaming updates endpoint"""
    data = request.json
    prompt = data.get('prompt')
    selected_files = data.get('selected_files', [])
    context_files = data.get('context_files', [])
    model = data.get('model', 'gpt-4-turbo-preview')
    base_branch = data.get('base_branch', 'main')

    if not prompt or not selected_files:
        return jsonify({"type": "error", "message": "Missing required fields"}), 400

    def generate():
        stream = StreamProcessor()
        change_type = data.get('change_type', 'github' if GITHUB_ENABLED else 'local')

        if change_type == 'github' and not GITHUB_ENABLED:
            message = "GitHub integration is not enabled; creating changes in local branch instead."
            logger.warning(message)
            yield stream.event('warning', {'message': message})
            change_type = 'local'

        repo = None
        original_branch = None
        new_branch = None

        try:
            # Read files content first
            with stream.stage("read_files"):
                files_content = {}
                for file_path in selected_files + context_files:
                    with open(file_path, 'r') as f:
                        files_content[file_path] = f.read()
                yield stream.event("info", {"message": f"Read {len(files_content)} files"})

            # Generate changes first, before creating any branches
            with stream.stage("generate_changes"):
                changes_response = stream.chat(
                    messages=[
                        {
                            "role": "system",
                            "content": """Generate changes for the specified files based on the prompt. You need to return the ENTIRE updated file(s). Follow the style guide and don't make another other changes, removing comments, etc.
* Do NOT add comments like \" # Rest of the functions remain the same ... \"
* Do NOT remove unrelated comments in the code
Return ONLY a JSON object with the following structure, no additional next or content before or after the JSON as follows, making sure the output is VALID JSON escaping newlines as \\n, etc:
{
  \"changes\": {
    \"file_path.txt\": \"new_content based on 'Requested changes' user prompt\",
    ...
  },
  \"new_files\": {
    \"new_file_path.txt\": \"content of the new file\",
    ...
  },
  \"summary\": \"detailed description of changes made\"
}"""
                        },
                        {
                            "role": "user",
                            "content": f"Files to modify:\n{json.dumps(files_content, indent=2)}\n\nRequested changes:\n{prompt}"
                        }
                    ],
                    model_name=model,
                    json_output=True,
                    extract_code_block=True
                )

                if not isinstance(changes_response, dict) or "changes" not in changes_response:
                    error_message = changes_response if isinstance(changes_response, str) else "Invalid response format from LLM"
                    logger.error(f"Bad changes response: {error_message}")
                    raise ValueError(error_message)

                changes = changes_response["changes"]
                new_files = changes_response.get("new_files", {})
                summary = changes_response.get("summary", "No summary provided")
                yield stream.event("info", {"message": "Changes generated"})

            # Generate branch name, PR title, commit message, and PR description based on the changes
            with stream.stage("generate_metadata"):
                try:
                    branch_description_commit = stream.chat(
                        messages=[
                            {
                                "role": "system",
                                "content": """Return ONLY a JSON object with the following structure, no additional text or content before or after the JSON as follows, making sure the output is VALID JSON escaping newlines as \\n, etc:
{
  \"branch_name\": \"feature-name\",
  \"pr_title\": \"Descriptive PR title\",
  \"pr_description\": \"Full PR description in markdown\",
  \"commit_message\": \"Commit message following best practices, first line summary (<72 chars), then blank line, then details\"
}
Branch name must:
- Use only lowercase letters, numbers, hyphens, and underscores
- Be descriptive of the changes made
- Maximum 50 characters
- Use snake_case for multiple words (e.g., update_auth_system)

PR title should:
- Be descriptive and concise
- Use spaces and capitalization as appropriate
- Not have the same restrictions as branch names
- Should not exceed 72 characters

Commit message should:
- Be in present tense
- First line summary less than 72 characters
- Second line should be blank
- Following lines can include detailed description
- The commit message should be formatted as per the following example:

[First line summary]

Prompt: [Original prompt]

Description: [Detailed description]

PR description should include:

## Prompt
[Original prompt]

## Summary of Changes
[Summary of changes]

### Technical Details
[Technical details of the changes]

### Files Modified
- [File 1]
- [File 2]
"""
                            },
                            {
                                "role": "user",
                                "content": f"Prompt: {prompt}\n\nChanges summary: {summary}\n\nFiles modified:\n{list(changes.keys()) + list(new_files.keys())}"
                            }
                        ],
                        model_name=model,
                        json_output=True,
                        extract_code_block=True
                    )

                    if not isinstance(branch_description_commit, dict):
                        logger.error(f"Bad branch/description/commit response: {str(branch_description_commit)}")
                        raise ValueError("Invalid response format from LLM")

                    generated_branch_name = branch_description_commit.get("branch_name", "").strip()
                    # Validate the generated branch name
                    if not is_valid_branch_name(generated_branch_name):
                        error_message = f"Invalid branch name generated: {generated_branch_name}. Using fallback."
                        logger.error(error_message)
                        yield stream.event("error", {"message": error_message})
                        generated_branch_name = ""
                    else:
                        yield stream.event("info", {"message": f"Generated branch name: {generated_branch_name}"})

                    # Build the final branch name
                    branch_name = f"GitIQ{('-' + generated_branch_name) if generated_branch_name else ''}-{int(time.time())}"

                    pr_title = branch_description_commit.get("pr_title", f"GitIQ: {generated_branch_name if generated_branch_name else branch_name}")

                    pr_description = branch_description_commit.get("pr_description", summary)
                    commit_message = branch_description_commit.get("commit_message", pr_description.split('\n')[0])

                except Exception as e:
                    error_message = f"Error generating branch name/description/commit message: {str(e)}. Using fallback."
                    logger.error(error_message)
                    yield stream.event("error", {"message": error_message})
                    branch_name = generate_branch_name()
                    pr_title = f"GitIQ: {branch_name}"
                    pr_description = f"## Changes\n{summary}"
                    commit_message = summary

                yield stream.event("info", {"message": "Branch name, commit message, and PR description generated"})

            # Now that we have the changes, create and checkout the branch
            repo = Repo(os.getcwd())
            original_branch = repo.active_branch

            with stream.stage("create_branch"):
                new_branch = repo.create_head(branch_name)
                new_branch.checkout()
                yield stream.event("info", {"message": f"Created branch: {branch_name}"})

            # Apply changes
            with stream.stage("apply_changes"):
                modified_files = []
                for file_path, content in changes.items():
                    if file_path in selected_files:  # Only modify selected files
                        logger.info(f"modified file: {file_path}")
                        with open(file_path, 'w') as f:
                            f.write(content)
                        modified_files.append(file_path)
                
                # Create new files
                for file_path, content in new_files.items():
                    logger.info(f"created new file: {file_path}")
                    with open(file_path, 'w') as f:
                        f.write(content)
                    modified_files.append(file_path)
                    repo.index.add([file_path])  # Add new file to git

                yield stream.event("info", {"message": f"Modified {len(modified_files)} files"})

            # Commit changes
            with stream.stage("commit_changes"):
                commit_message_with_model = f"{commit_message}\n\nModel: {model}"
                repo.index.add(modified_files)
                repo.index.commit(
                    commit_message_with_model,
                    author=GIT_BOT,
                    committer=GIT_BOT
                )
                yield stream.event("info", {"message": "Changes committed"})

            # Push changes to remote repository if change_type is 'github'
            if change_type == 'github':
                with stream.stage("push_changes"):
                    try:
                        repo.git.push('--set-upstream', 'origin', branch_name)
                        yield stream.event("info", {"message": f"Branch '{branch_name}' pushed to remote 'origin'"})
                    except Exception as e:
                        error_message = f"Failed to push branch '{branch_name}' to remote 'origin': {str(e)}"
                        logger.error(error_message)
                        yield stream.event("error", {"message": error_message})
                        raise
            else:
                yield stream.event("info", {"message": f"Local branch '{branch_name}' created but not pushed to remote"})

            # Create PR if change_type is 'github'
            if change_type == 'github':
                with stream.stage("create_pr"):
                    pr_description_with_model = f"{pr_description}\n\nModel: {model}"
                    pr_url = create_github_pr(
                        pr_title,
                        branch_name,
                        pr_description_with_model,
                        base_branch
                    )
                    if pr_url:
                        yield stream.event("complete", {
                            "message": f"GitHub PR created successfully: <a href=\"{pr_url}\" target=\"_blank\">{pr_title}</a>",
                            "branch": branch_name,
                            "pr_url": pr_url,
                            "pr_title": pr_title,
                            "pr_description": pr_description_with_model
                        })
                    else:
                        error_message = "Failed to create GitHub PR."
                        logger.error(error_message)
                        yield stream.event("error", {"message": error_message})
                        # Optionally, you can choose to raise an error or proceed
            else:
                pr_url = f"local://{branch_name}"
                pr_title = f"GitIQ: {generated_branch_name if generated_branch_name else branch_name}"
                pr_description_with_model = f"{pr_description}\n\nModel: {model}"
                yield stream.event("complete", {
                    "pr_url": pr_url,
                    "link_open": pr_url,
                    "message": "Local branch created successfully",
                    "branch": branch_name,
                    "pr_title": pr_title,
                    "pr_description": pr_description_with_model
                })

        except Exception as e:
            logger.exception("Error processing request")
            if repo and original_branch:
                cleanup_failed_operation(repo, original_branch, new_branch.name if new_branch else None, change_type)
            yield stream.event("error", {"message": str(e)})

    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/repo/branches')
def repo_branches():
    """Get list of local and remote branches."""
    try:
        repo = Repo(os.getcwd())
        current_branch = repo.active_branch.name

        local_branches = [head.name for head in repo.heads]
        remote_branches = [ref.name for ref in repo.remotes.origin.refs]

        return jsonify({
            "current_branch": current_branch,
            "local_branches": local_branches,
            "remote_branches": remote_branches
        })
    except Exception as e:
        logger.error(f"Error getting branches: {str(e)}")
        return jsonify({"type": "error", "message": str(e)}), 500

@app.route('/api/repo/switch-branch', methods=['POST'])
def switch_branch():
    """Switch to a different local branch."""
    data = request.json
    branch_name = data.get('branch')

    if not branch_name:
        return jsonify({"type": "error", "message": "Missing 'branch' parameter"}), 400

    try:
        repo = Repo(os.getcwd())

        if repo.is_dirty(untracked_files=True):
            return jsonify({"type": "error", "message": "Cannot switch branches with uncommitted changes"}), 400

        if branch_name not in [head.name for head in repo.heads]:
            return jsonify({"type": "error", "message": f"Branch '{branch_name}' does not exist"}), 400

        repo.git.checkout(branch_name)
        current_branch = repo.active_branch.name

        return jsonify({"type": "complete", "message": f"Switched to branch {branch_name}", "current_branch": current_branch})
    except Exception as e:
        logger.error(f"Error switching branches: {str(e)}")
        return jsonify({"type": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5500)))
