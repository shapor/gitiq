"""
github_integration.py - GitHub API integration for GitIQ
"""
import os
import json
import logging
from github import Github
from github.GithubException import GithubException

logger = logging.getLogger(__name__)

def load_github_config():
    """Load GitHub configuration from config.json"""
    with open('config.json') as f:
        config = json.load(f)
    return config.get('github', {})

def create_github_pr(pr_title, branch_name, pr_description, base_branch):
    """Create a GitHub Pull Request"""
    github_config = load_github_config()
    
    if not github_config.get('enabled', False):
        logger.warning("GitHub integration is not enabled in config.json")
        return None

    access_token = os.getenv(github_config.get('access_token'))
    repo_owner = github_config.get('repo_owner')
    repo_name = github_config.get('repo_name')

    if not all([access_token, repo_owner, repo_name]):
        logger.error("Missing required GitHub configuration")
        raise ValueError("Incomplete GitHub configuration")

    try:
        g = Github(access_token)
        repo = g.get_repo(f"{repo_owner}/{repo_name}")
        
        # Create pull request
        pr = repo.create_pull(
            title=pr_title,
            body=pr_description,
            head=branch_name,
            base=base_branch  # Use the specified base_branch
        )
        
        logger.info(f"Created GitHub PR: {pr.html_url}")
        return pr.html_url
    
    except GithubException as e:
        logger.error(f"GitHub API error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating GitHub PR: {str(e)}")
        raise
