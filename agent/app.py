"""
app.py - Main Flask application for GitIQ
"""
import os
import json
import logging
from flask import Flask, request, jsonify, Response
from git import Repo, InvalidGitRepositoryError
from git.exc import GitCommandError

from llm_integration import load_llm_config, list_models, chat_completion
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

# Load LLM configuration
load_llm_config('config.json')

def get_repo_status():
    """Get Git repository status information"""
    try:
        repo = Repo(os.getcwd())
        return {
            "is_git_repo": True,
            "has_credentials": bool(repo.git.config("--get", "user.name", with_exceptions=False)),
            "current_branch": repo.active_branch.name
        }
    except InvalidGitRepositoryError:
        return {
            "is_git_repo": False,
            "has_credentials": False,
            "current_branch": None
        }

def get_file_structure(repo_path="."):
    """Get repository file structure with Git status"""
    try:
        repo = Repo(repo_path)
        status = repo.index.diff(None)
        untracked = repo.untracked_files

        def get_git_status(file_path):
            if file_path in untracked:
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
        for root, _, files in os.walk(repo_path):
            if ".git" in root:
                continue
            for file in files:
                file_path = os.path.join(root, file).replace("\\", "/")
                if file_path.startswith("./"):
                    file_path = file_path[2:]

                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        is_binary = '\0' in content
                        lines = len(content.splitlines()) if not is_binary else 0
                        tokens = len(content.split()) if not is_binary else 0  # TODO: use tiktoken to count actual tokens
                except:
                    is_binary = True
                    lines = 0
                    tokens = 0

                result.append({
                    "path": file_path,
                    "size": os.path.getsize(file_path),
                    "mtime": int(os.path.getmtime(file_path)),
                    "is_binary": is_binary,
                    "lines": lines,
                    "tokens": tokens,
                    "git_status": get_git_status(file_path),
                    "diff": None  # TODO: Add diff implementation if needed
                })
        return result
    except InvalidGitRepositoryError:
        return []

def create_branch_name(description):
    """Generate semantic branch name from description"""
    return chat_completion(
        messages=[
            {"role": "system", "content": "Generate a short, kebab-case branch name from the description. Use only lowercase letters, numbers, and hyphens. Max length 50 chars. Format: GitIQ-{name}"},
            {"role": "user", "content": description}
        ],
        model_name="gpt-3.5-turbo"
    ).strip()

def generate_file_changes(prompt, files, model_name):
    """Generate file changes using LLM"""
    try:
        files_content = {}
        for file_path in files:
            with open(file_path, 'r') as f:
                files_content[file_path] = f.read()

        return chat_completion(
            messages=[
                {"role": "system", "content": "Generate changes for the specified files based on the prompt. Return a JSON object with file paths as keys and new file contents as values."},
                {"role": "user", "content": f"Files to modify:\n{json.dumps(files_content, indent=2)}\n\nRequested changes:\n{prompt}"}
            ],
            model_name=model_name,
            json_output=True
        )
    except Exception as e:
        logger.error(f"Error generating changes: {str(e)}")
        raise

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
        return jsonify({"error": "Missing required fields"}), 400

    def generate():
        stream = StreamProcessor()
        try:
            repo = Repo(os.getcwd())

            # Create branch
            with stream.stage("create_branch"):
                branch_name = create_branch_name(prompt)
                current = repo.active_branch
                new_branch = repo.create_head(branch_name)
                new_branch.checkout()
                yield stream.event("create_branch", {"branch": branch_name})

            # Generate changes
            with stream.stage("generate_changes"):
                changes = generate_file_changes(prompt, selected_files + context_files, model)
                yield stream.event("generate_changes", {})

            # Apply changes
            with stream.stage("apply_changes"):
                for file_path, content in changes.items():
                    if file_path in selected_files:
                        with open(file_path, 'w') as f:
                            f.write(content)
                yield stream.event("apply_changes", {"files": list(changes.keys())})

            # Commit changes
            with stream.stage("commit"):
                repo.index.add(list(changes.keys()))
                commit_message = f"""Model: {model}

Prompt: {prompt}

Files modified:
{chr(10).join(f"- {f}" for f in changes.keys())}"""
                repo.index.commit(commit_message)
                yield stream.event("commit", {"hash": repo.head.commit.hexsha})

            # Create PR (placeholder - actual GitHub/GitLab integration needed)
            with stream.stage("create_pr"):
                pr_url = f"local://{branch_name}"  # Placeholder
                yield stream.event("create_pr", {"url": pr_url})

            # Cleanup
            current.checkout()

            yield stream.event("complete", {})

        except Exception as e:
            logger.exception("Error processing request")
            yield stream.event("error", {"error": str(e)})

            # Attempt cleanup on error
            try:
                current.checkout()
            except:
                pass

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5500)))
