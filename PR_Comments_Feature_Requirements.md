# GitIQ PR Comments - Feature Requirements

## Overview
GitIQ will handle GitHub PR comments by running a simple local process that watches PRs and responds like a human team member would - either with clarifying questions as comments or with new commits containing requested changes.

## Core Principles
- Keep it extremely simple - no databases, no webhooks, no complex state
- Run entirely locally like the rest of GitIQ
- Communicate only through GitHub PR comments
- Add only new commits, never modify history
- Behave like a helpful team member would

## Architecture
- Single long-running local Python process
- No external services or webhooks required
- No state tracking needed
- Polls GitHub API periodically for new comments
- Zero persistence required

## Core Workflow
1. On startup:
   - Query all open PRs in repository
   - Check for any unresponded @GitIQ mentions
   - Process any found mentions

2. While running:
   - Poll periodically for new comments on open PRs
   - Look for @GitIQ mentions or replies to GitIQ comments
   - Process any new comments requiring response

3. When GitIQ sees a comment needing response:
   - If requirements are clear → make requested changes as new commit
   - If clarification needed → reply with questions in PR thread
   - No special command syntax beyond initial @GitIQ mention

## State Management
Zero persistent state required. On startup or restart:
1. Query all open PRs in the repository
2. Look for any unresponded @GitIQ mentions
3. Process and respond as needed

While running:
- Track active PRs in memory only
- No persistence needed
- No state files
- Full context available from PR threads

On process termination:
- All state can be safely discarded
- Next startup will re-scan PRs for missed mentions

## Error Handling
- Process dies → restart and re-scan PRs for any missed mentions
- API rate limiting → back off and retry
- Multiple instances → safe due to idempotent operations
- Network issues → retry on next poll interval
- Unclear requirements → ask in PR thread like a human would

## Security
- Uses local git credentials
- No additional authentication needed
- No incoming network connections
- No sensitive data storage

## Limitations
- Must be running to respond to comments
- Small latency due to polling interval
- One instance per local repository

## Non-Requirements
- No webhooks
- No databases
- No persistence
- No state tracking of conversations
- No special command syntax
- No history modification
- No force pushes

## Integration with Existing GitIQ
- Uses same git operations code
- Uses same LLM interaction code
- Uses same file handling code
- Maintains same simple philosophy
- Fits naturally into existing workflow

## Example Interactions

### Simple Change Request
```
User: @GitIQ please add input validation to this function
GitIQ: *makes commit with validation logic*
```

### Needs Clarification
```
User: @GitIQ add rate limiting here
GitIQ: What rate limit would you prefer? Based on current usage patterns,
      I'd suggest either 100/min or 1000/min.
User: Let's go with 100/min
GitIQ: *makes commit implementing rate limit*
```

### Multi-Step Change
```
User: @GitIQ we should switch to JWT auth
GitIQ: I'll help with that. A few questions first:
      1. What expiration time should we use for tokens?
      2. Should we support refresh tokens?
      3. Do we need to maintain backward compatibility?
User: 24h expiration, yes to refresh tokens, no backward compatibility needed
GitIQ: *makes commit implementing JWT auth with specified requirements*
```