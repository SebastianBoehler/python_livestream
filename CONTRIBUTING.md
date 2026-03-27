# Contributing

Thanks for contributing.

## Scope

This repository is primarily an operational livestreaming system. Changes should improve one or more of these areas:

- stream reliability
- playout continuity
- capture quality
- prompt or TTS quality
- deployment ergonomics
- observability
- test coverage

## Development Guidelines

- Keep modules focused and avoid duplicated logic.
- Prefer explicit code over clever shortcuts.
- Do not add mock data or silent fallbacks unless they are intentionally part of the feature.
- Keep files small and split code when a file starts becoming difficult to reason about.
- Document new environment variables in [.env.example](/Users/sebastianboehler/Documents/GitHub/python_livestream/.env.example) and [README.md](/Users/sebastianboehler/Documents/GitHub/python_livestream/README.md).

## Before Opening a Pull Request

Run:

```bash
python -m py_compile $(git ls-files '*.py')
python -m unittest discover -s tests -p 'test_*.py' -v
```

If you changed Docker behavior, also run:

```bash
docker build -t python-livestream .
```

## Pull Request Expectations

- Describe the operational problem the change solves.
- Keep commits logically grouped.
- Call out any new environment variables, deployment assumptions, or provider requirements.
- Include tests for behavior changes where practical.
- Mention residual risk or areas you could not verify.

## Reporting Bugs

When filing an issue, include:

- the capture backend in use
- host OS or container environment
- provider configuration
- relevant logs around FFmpeg speed, latency, and queue state
- steps to reproduce

## Code of Conduct

Please keep collaboration direct, respectful, and technically grounded. Disagreement is fine. Low-signal noise is not.
