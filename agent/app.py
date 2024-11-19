"""
app.py - Main Flask application for GitIQ
"""
import os
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, Response, send_from_directory
from git import Repo, InvalidGitRepositoryError
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
    GIT_AUTHOR = config.get('git', {}).get('author', 'GitIQ-bot <gitiq-bot@github.com>')
    GIT_COMMITTER = config.get('git', {}).get('committer', 'GitIQ-bot <gitiq-bot@github.com>')

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
            repo = Repo(os.getcwd())
            original_branch = repo.active_branch

            # Create branch
            with stream.stage("create_branch"):
                branch_name = stream.chat(
                    messages=[
                        {"role": "system", "content": "Generate a short, kebab-case branch name from the description. Use only lowercase letters, numbers, and hyphens. Max length 50 chars. Format: GitIQ-{name}"},
                        {"role": "user", "content": prompt}
                    ],
                    model_name=model
                ).strip()
                new_branch = repo.create_head(branch_name)
                new_branch.checkout()
                yield stream.event("info", {"message": f"Created branch: {branch_name}"})

            # Read files content
            with stream.stage("read_files"):
                files_content = {}
                for file_path in selected_files + context_files:
                    with open(file_path, 'r') as f:
                        files_content[file_path] = f.read()
                yield stream.event("info", {"message": f"Read {len(files_content)} files"})

            # Generate changes and description in parallel
            with ThreadPoolExecutor() as executor:
                with stream.stage("generate_changes"):
                    changes_future = executor.submit(lambda: stream.chat(
                        messages=[
                            {"role": "system", "content": "Generate changes for the specified files based on the prompt. Return a JSON object with file paths as keys and new file contents as values."},
                            {"role": "user", "content": f"Files to modify:\n{json.dumps(files_content, indent=2)}\n\nRequested changes:\n{prompt}"}
                        ],
                        model_name=model,
                        json_output=True
                    ))

                with stream.stage("generate_description"):
                    description_future = executor.submit(lambda: stream.chat(
                        messages=[
                            {
                                "role": "system",
                                "content": """Generate a detailed PR description with:
                                1. Original prompt
                                2. Summary of changes and their impact
                                3. Technical details of implementation
                                4. List of modified files
                                Use markdown formatting."""
                            },
                            {
                                "role": "user",
                                "content": f"Prompt: {prompt}\n\nFiles to be modified: {', '.join(selected_files)}"
                            }
                        ],
                        model_name=model
                    ))

                changes = changes_future.result()
                yield stream.event("info", {"message": "Changes generated"})

                pr_description = description_future.result()
                yield stream.event("info", {"message": "PR description generated"})

            # Apply changes
            with stream.stage("apply_changes"):
                modified_files = []
                for file_path, content in changes.items():
                    if file_path in selected_files:
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
                    author=GIT_AUTHOR,
                    committer=GIT_COMMITTER
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
