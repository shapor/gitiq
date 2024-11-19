# GitIQ

GitIQ is a new approach to AI pair programming that uses Git as the interface rather than embedding in an IDE.

## Quick Start

To run the application:

```
OPENAI_API_KEY=xxxx python agent/app.py
```

## Documentation

- [Product Requirements Document](PRD.md)
- [API Specification](API.md)
- [Style Guide](Style_Guide.md)

## Overview

While tools like GitHub Copilot and Cursor excel at in-IDE code generation, developers often want to make more substantial, multi-file changes that are better suited to Pull Requests. GitIQ allows developers to describe changes in natural language and get back complete PRs, using Git commits to maintain a clear history of AI-human collaboration.

## Key Features

- Uses Git as the primary interface instead of IDE integration
- Preserves context and decision-making through commit messages
- Handles multi-file changes as coherent units of work
- Creates reviewable PRs rather than inline code suggestions
- Works with any editor/IDE since changes flow through Git

## Contributing

Please read our [Style Guide](Style_Guide.md) before contributing to this project.

## License

[MIT License](LICENSE)
