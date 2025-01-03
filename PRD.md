# GitIQ Requirements Specification

## Overview
GitIQ is a new approach to AI pair programming that uses Git as the interface rather than embedding in an IDE. While tools like GitHub Copilot and Cursor excel at in-IDE code generation, developers often want to make more substantial, multi-file changes that are better suited to Pull Requests. GitIQ allows developers to describe changes in natural language and get back complete PRs, using Git commits to maintain a clear history of AI-human collaboration.

## Key Differentiators
- Uses Git as the primary interface instead of IDE integration
- Preserves context and decision-making through commit messages
- Handles multi-file changes as coherent units of work
- Creates reviewable PRs rather than inline code suggestions
- Works with any editor/IDE since changes flow through Git
- Supports multiple LLM providers and models through flexible configuration

## Core Workflow
1. Developer describes desired changes in natural language
2. GitIQ creates a semantically-named branch with a unique timestamp
3. AI makes changes across selected files
4. Changes are committed with detailed messages including prompts and model metadata
5. **Optional**: PR is created for review if GitHub integration is enabled
6. Future: Comments on PR become new prompts for iterative refinement **(post-MVP)**

## Requirements

### Git Integration
- Creates feature branch with AI-generated semantic name appended to 'GitIQ' and timestamp (format: `GitIQ-{generated_name}-{timestamp}`)
- Sets git user.name and user.email for AI commits (configurable in config.json)
- Commits changes with:
  - Original prompt as commit message
  - AI-generated description of changes
  - Includes LLM model name/version used
  - Optional: includes prompt tokens used and other metadata **(post-MVP)**
- Optionally opens PR with:
  - Uses AI-generated PR title (less restricted than branch names)
  - Original prompt as PR description
  - AI-generated summary of changes and their impact
  - Links to attached context files **(post-MVP)**
  - Standard PR template if repo has one **(post-MVP)**

### User Interface
#### Prompt Interface
- Large text input field for main prompt
- Slider or toggle for **Change Type** with options:
  - **Local Branch**: Creates changes in a local git branch
  - **GitHub PR**: Pushes branch and creates a GitHub Pull Request
- Clear button to reset input **(post-MVP)**
- Submit button to generate changes
- Dropdown to select LLM model

#### File Selection
- Simple list view of repository files
- Checkboxes next to each file
- Search/filter capability for large repos **(post-MVP)**
- Initially collapses node_modules and other common ignore patterns **(post-MVP)**
- Shows git status (modified, untracked) next to files
- Basic directory structure visible
- Displays token count for selected files

#### Context Addition
- Basic ability to attach files for context
- Drag and drop support for files **(post-MVP)**
- Preview of attached content **(post-MVP)**
- Clear option for attached files **(post-MVP)**

### Processing
- Async processing of change generation
- Simple loading indicator
- Cancel capability for long-running operations **(post-MVP)**
- Basic error handling with user feedback
- Streaming updates during change generation process

### Security & Authentication
- Runs only on localhost
- No additional authentication needed (assumes local user is authorized)
- Uses existing git config and credentials for commits/PRs
- Configurable LLM API endpoints and keys

### Error States to Handle
1. Not in git repository
2. Dirty working directory **(post-MVP)**
3. Network connectivity issues
4. LLM API failures
5. File permission issues **(post-MVP)**
6. Invalid file selections
7. Invalid LLM configuration

### Success Metrics
- Time from prompt to branch/pr creation **(post-MVP)**
- PR acceptance rate **(post-MVP)**
- Number of iteration cycles needed **(post-MVP)**
- File selection accuracy **(post-MVP)**
- Basic error tracking
- Token usage and cost tracking

### Example Commit Message Format
```
Implement JWT-based authentication system to replace session cookies

Model: gpt-4-turbo-preview

Prompt: Update the user authentication to use JWT tokens instead of session cookies

Description: Implemented JWT-based authentication system to replace session cookies, 
enhancing security and enabling stateless authentication. The changes include new 
JWT token generation, validation logic, and updated user session management.

Files modified:
- auth.py
- user_model.py
```

### Example PR Title
```
Implement JWT-based Authentication System
```

### Example PR Description Format
```
## Prompt
Update the user authentication to use JWT tokens instead of session cookies

## Summary of Changes
This PR modernizes our authentication system by replacing session-based cookies 
with JWT tokens. This change brings several benefits:
- Enables stateless authentication, reducing database load
- Improves security through cryptographic signatures
- Facilitates better cross-domain authentication
- Simplifies authentication for API clients

The implementation includes new JWT token generation and validation logic in 
auth.py, along with updates to the user model to support token-based sessions.

### Technical Details
- Added JWT token generation and validation functions
- Updated user authentication flow to use tokens
- Modified session management to be stateless
- Added token refresh mechanism
- Updated relevant tests

### Files Modified
- auth.py
- user_model.py

Model: gpt-4-turbo-preview
```

### Configuration
GitIQ uses a `config.json` file for various settings, including:
- Git user configuration
- LLM API endpoints and keys
- Available models and their configurations
- Default change type (`local` or `github`)

### New Feature: Change Type Selection
Users can now choose the type of change they want to create:
- **Local Branch**: The changes are committed to a new local branch.
- **GitHub PR**: The changes are pushed to a remote repository and a Pull Request is created on GitHub.

This selection is made via a slider or toggle in the prompt interface.

### Updated Branch Naming Convention
GitIQ now simplifies the branch name creation logic:
- The branch name starts with `GitIQ`
- Attempts to append the AI-generated branch name (without `GitIQ-` prefix)
- Always appends a timestamp to ensure uniqueness (format: `GitIQ-{generated_name}-{timestamp}`)
- If no valid branch name is generated, it defaults to `GitIQ-{timestamp}`

### Updated PR Title Generation
- PR titles are now generated separately from branch names
- PR titles are less restricted and can include spaces, capitalization, and special characters
- Helps make PRs more readable and descriptive

Questions for immediate implementation:
1. Should we limit the number of context files for MVP?
2. What should be the default behavior if no files are selected?
3. Should we require a minimum prompt length?
4. Should we have a maximum length for LLM-generated branch names?
5. How should we handle cases where the LLM suggests changes to files that weren't selected?
