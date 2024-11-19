"""
app.py - Main Flask application for GitIQ
"""
import os
import json
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, Response, send_from_directory
from git import Repo, InvalidGitRepositoryError, Actor
from git.exc import GitCommandError

from llm_integration import load_llm_config, list_models
from stream_events import StreamProcessor

def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - level=%(levelname)s - %(message)s"))
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
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

# Load LLM configuration
load_llm_config('config.json')

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
                            tokens = len(content.split())
                except UnicodeDecodeError:
                    is_binary = True

                git_status = get_git_status(file_path)
                if git_status == "modified":
                    try:
                        diff = repo.git.diff(file_path)
                    except:
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

def generate_branch_name(summary):
    """Generate a semantic branch name from the change summary"""
    try:
        return f"GitIQ-{int(time.time())}"
    except Exception as e:
        logger.error(f"Error generating branch name: {str(e)}")
        return f"GitIQ-{int(time.time())}"

def cleanup_failed_operation(repo, original_branch, new_branch_name):
    """Clean up after failed PR creation"""
    try:
        if original_branch:
            original_branch.checkout()
        if new_branch_name in repo.heads:
            repo.delete_head(new_branch_name, force=True)
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

    if not prompt or not selected_files:
        return jsonify({"type": "error", "message": "Missing required fields"}), 400

    def generate():
        stream = StreamProcessor()
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
                            "content": """Generate changes for the specified files based on the prompt. 
                            Return ONLY a JSON object with the following structure, no additional next or content before or after the JSON as follows:
                            {
                                "changes": {
                                    "file_path": "new_content",
                                    ...
                                },
                                "summary": "detailed description of changes made"
                            }"""
                        },
                        {
                            "role": "user",
                            "content": f"Files to modify:\n{json.dumps(files_content, indent=2)}\n\nRequested changes:\n{prompt}"
                        }
                    ],
                    model_name=model,
                    json_output=True
                )
                if isinstance(changes_response, str):
                    try:
                        changes_response = json.loads(changes_response)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON response: {changes_response}")
                        raise ValueError("Invalid JSON response from LLM")

                if not isinstance(changes_response, dict) or "changes" not in changes_response:
                    logger.error(f"Bad changes response: {str(changes_response)}")
                    raise ValueError("Invalid response format from LLM")

                changes = changes_response["changes"]
                summary = changes_response.get("summary", "No summary provided")
                yield stream.event("info", {"message": "Changes generated"})

            # Generate branch name and PR description based on the changes
            with stream.stage("generate_metadata"):
                try:
                    branch_and_description = stream.chat(
                        messages=[
                            {
                                "role": "system",
                                "content": """Return ONLY a JSON object with the following structure, no additional next or content before or after the JSON as follows:
{
  "branch_name": "GitIQ-feature-name",
  "pr_description": "Full PR description in markdown"
}
Branch name must:
- Start with GitIQ-
- Use only lowercase letters, numbers, and hyphens
- Maximum 50 characters"""
                            },
                            {
                                "role": "user",
                                "content": f"Prompt: {prompt}\n\nChanges summary: {summary}"
                            }
                        ],
                        model_name=model,
                        json_output=True
                    )

                    if isinstance(branch_and_description, str):
                        try:
                            branch_and_description = json.loads(branch_and_description)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse JSON response: {branch_and_description}")
                            raise ValueError("Invalid JSON response from LLM")

                    if not isinstance(branch_and_description, dict):
                        logger.error(f"Bad branch/description response: {str(branch_and_description)}")
                        raise ValueError("Invalid response format from LLM")

                    branch_name = branch_and_description.get("branch_name", "")
                    if not branch_name.startswith("GitIQ-") or len(branch_name) > 50:
                        branch_name = generate_branch_name(summary)

                    pr_description = branch_and_description.get("pr_description", summary)
                except Exception as e:
                    logger.error(f"Error generating branch name/description: {str(e)}")
                    branch_name = generate_branch_name(summary)
                    pr_description = summary

                yield stream.event("info", {"message": "Branch name and PR description generated"})

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
                        with open(file_path, 'w') as f:
                            f.write(content)
                        modified_files.append(file_path)
                yield stream.event("info", {"message": f"Modified {len(modified_files)} files"})

            # Commit changes
            with stream.stage("commit_changes"):
                repo.index.add(modified_files)
                commit_message = f"""
{pr_description}

Model: {model}
"""
                repo.index.commit(
                    commit_message,
                    author=GIT_BOT,
                    committer=GIT_BOT
                )
                yield stream.event("info", {"message": "Changes committed"})

            # Create PR (placeholder)
            with stream.stage("create_pr"):
                pr_url = f"local://{branch_name}"
                yield stream.event("complete", {
                    "pr_url": pr_url,
                    "message": "PR created successfully",
                    "branch": branch_name
                })

        except Exception as e:
            logger.exception("Error processing request")
            if repo and original_branch:
                cleanup_failed_operation(repo, original_branch, new_branch.name if new_branch else None)
            yield stream.event("error", {"message": str(e)})

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5500)))
