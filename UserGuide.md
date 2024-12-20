# GitIQ User Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running GitIQ](#running-gitiq)
5. [Using the Interface](#using-the-interface)
6. [Understanding Output Messages](#understanding-output-messages)

[Previous sections remain the same until 'Using the Interface'...]

## Understanding Output Messages

When using GitIQ, you'll see a series of status messages that help you track the progress of your request. Here's what they mean:

1. **Initialization Message**
   ```
   [11:48:41 PM] GitIQ initialized successfully
   ```
   This confirms that the system is ready to process requests.

2. **Request Details**
   ```
   [11:50:49 PM] A new request was dispatched for 2 files (2062 tokens) to model Claude 3.5 Sonnet (latest)
   [11:50:49 PM] info: Read 2 files
   ```
   - Shows how many files are being processed
   - Displays the total token count
   - Indicates which AI model is being used

3. **Generation Status**
   ```
   [11:51:31 PM] info: Changes generated
   ```
   Confirms that the AI has completed generating the requested changes.

4. **LLM Statistics**
   ```
   [11:51:31 PM] LLM Stats - Total Tokens: 5964, Prompt Tokens: 3005, Completion Tokens: 2959, Cost: $0.0534
   ```
   - Total Tokens: Combined input and output tokens
   - Prompt Tokens: Tokens used in the input
   - Completion Tokens: Tokens generated in the response
   - Cost: Estimated cost for this operation

5. **Branch and Commit Information**
   ```
   [11:51:37 PM] info: Generated branch name: update_pr_selection_docs
   [11:51:37 PM] info: Branch name, commit message, and PR description generated
   [11:51:38 PM] info: Created branch: GitIQ-update_pr_selection_docs-1734681097
   ```
   Shows the progress of creating a new branch and preparing the changes.

6. **File Modification Status**
   ```
   [11:51:38 PM] info: Modified 2 files
   [11:51:38 PM] info: Changes committed
   ```
   Confirms which files were changed and that changes were committed.

7. **Final Status**
   ```
   [11:51:38 PM] info: Local branch 'GitIQ-update_pr_selection_docs-1734681097' created but not pushed to remote
   [11:51:38 PM] complete: Local branch created successfully
   ```
   - For local branches: Shows the branch name where changes were made
   - For GitHub PRs: Provides a link to the created Pull Request

8. **Cost Tracking**
   Multiple LLM Stats entries may appear, showing costs for different operations:
   ```
   [11:51:37 PM] LLM Stats - Total Tokens: 946, Prompt Tokens: 547, Completion Tokens: 399, Cost: $0.0076
   ```
   This helps you monitor the cost of each operation.

[Rest of the original content remains the same...]
