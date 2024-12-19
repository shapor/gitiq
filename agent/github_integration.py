"""github_integration.py - GitHub API integration for GitIQ"""
import os
import json
import time
import logging
import threading
from github import Github, PullRequest
from github.GithubException import GithubException
from github.IssueComment import IssueComment
from github.PullRequestComment import PullRequestComment

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

def process_pr_comments():
    """Start a background thread to process PR comments"""
    def comment_processor():
        github_config = load_github_config()
        if not github_config.get('enabled', False):
            logger.warning("GitHub integration not enabled, skipping PR comment processing")
            return

        access_token = os.getenv(github_config.get('access_token'))
        repo_owner = github_config.get('repo_owner')
        repo_name = github_config.get('repo_name')

        if not all([access_token, repo_owner, repo_name]):
            logger.error("Missing required GitHub configuration")
            return

        g = Github(access_token)
        repo = g.get_repo(f"{repo_owner}/{repo_name}")

        while True:
            try:
                # Get all open PRs
                open_prs = repo.get_pulls(state='open')
                
                for pr in open_prs:
                    # Get issue comments that mention @GitIQ
                    issue_comments = pr.get_issue_comments()
                    for comment in issue_comments:
                        if not isinstance(comment, IssueComment):
                            continue
                        if not hasattr(comment, 'body'):
                            logger.warning(f"Comment ID {comment.id} does not have a body.")
                            continue
                        logger.info(f"Processing issue comment ID {comment.id}: {comment.body}")
                        if '@gitiq-bot' in comment.body and not comment.body.startswith('GitIQ:'):
                            try:
                                # Process the comment and generate a response
                                response = "GitIQ: I'll help with that. This feature is coming soon!"
                                pr.create_issue_comment(response)
                                logger.info(f"Responded to issue comment in PR #{pr.number} with ID {comment.id}")
                            except Exception as e:
                                logger.error(f"Error processing issue comment in PR #{pr.number}: {str(e)}")

                    # Get review comments that mention @GitIQ
                    review_comments = pr.get_review_comments()
                    for review_comment in review_comments:
                        if not isinstance(review_comment, PullRequestComment):
                            continue
                        if not hasattr(review_comment, 'body'):
                            logger.warning(f"Review comment ID {review_comment.id} does not have a body.")
                            continue
                        logger.info(f"Processing review comment ID {review_comment.id}: {review_comment.body}")
                        if '@gitiq-bot' in review_comment.body and not review_comment.body.startswith('GitIQ:'):
                            try:
                                # Process the review comment and generate a response
                                response = "GitIQ: I'll assist with that change. Updating the code accordingly."
                                pr.create_issue_comment(response)
                                logger.info(f"Responded to review comment in PR #{pr.number} with ID {review_comment.id}")
                            except Exception as e:
                                logger.error(f"Error processing review comment in PR #{pr.number}: {str(e)}")

                # Sleep for a while before checking again
                time.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in PR comment processor: {str(e)}")
                time.sleep(300)  # On error, wait 5 minutes before retrying

    # Start the comment processor in a background thread
    thread = threading.Thread(target=comment_processor, daemon=True)
    thread.start()
    logger.info("Started PR comment processor thread")
