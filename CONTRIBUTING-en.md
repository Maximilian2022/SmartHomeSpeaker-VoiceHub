# Contributing Guide

[日本語 (Japanese)](CONTRIBUTING.md) | **English**

Thank you for your interest in contributing to "Smart Home Speaker Voice Hub"!
We warmly welcome all forms of contributions, including bug reports, feature suggestions, documentation improvements, and pull requests.

---

## 1. Questions and Idea Discussions

If you have questions such as "Would this feature be helpful?", "How does this configuration work?", or "How should this integration be implemented?", feel free to post in **[GitHub Discussions](https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub/discussions)**.

Discussions provide a great place for brainstorming before filing an issue or exchanging ideas with fellow users.

---

## 2. Bug Reports and Feature Requests (Issues)

Please submit bug reports and feature requests via [GitHub Issues](https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub/issues).

- **Bug Reports**: Please include observed behavior, step-by-step reproduction instructions, expected behavior, your environment (Docker / OS / speaker models), and relevant logs (ensure passwords, auth tokens, and personal details are redacted).
- **Feature Requests**: Describing the problem you wish to solve and providing concrete use cases helps us evaluate and prioritize proposals more effectively.

*Note: For security vulnerabilities, please do not file a public issue; follow the private reporting process outlined in [SECURITY-en.md](SECURITY-en.md).*

---

## 3. Development Principles & Architecture Guidelines

When adding or modifying code in this project, please adhere to the following architectural guidelines:

1. **Backend is Python-First**:
   - This project has fully migrated from Node.js to Python 3.12+ (FastAPI).
   - All backend logic and new features must be written in Python unless there is a strong, justified reason.
2. **Frontend is Vanilla JS / CSS**:
   - The Web UI (under `public/`) uses Vanilla JavaScript and Vanilla CSS without requiring any external build tools or bundlers.
   - To preserve lightweight operation and maintainability, please avoid introducing heavy UI frameworks.
3. **Homebridge Plugin**:
   - The plugin under `plugins/homebridge-voicehub/` is written in TypeScript and runs in a Node.js environment. When modifying the plugin, compile it with `npm run build` and ensure `dist/` is generated cleanly.
4. **Configuration & Environment Variables**:
   - Environment variables must be declared and managed via `pydantic-settings` (`app/core/config.py`). Also update `.my.env.sample` with sample values for any new variables.

---

## 4. Setting Up Local Development

### Using Docker (Recommended)
```bash
# 1. Clone the repository
git clone https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub.git
cd SmartHomeSpeaker-VoiceHub

# 2. Prepare environment configuration
cp .my.env.sample .my.env

# 3. Build and launch container
docker compose up --build
```
*Note: The repository includes a `docker-compose.override.yml` file. Running `docker compose up` automatically binds local source files (`./app`, `./public`) into the container, enabling instant hot-reloading during development.*

Open your browser and navigate to `http://localhost:8080` to verify that the application is running.

### Using a Local Python Environment
```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt

# Start the development server
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

---

## 5. Running Tests

After making changes, always run the existing unit tests and smoke tests to ensure they all pass. We recommend running tests inside the Docker container to match the production runtime environment (Python 3.14 + system audio libraries).

### Running Tests in Docker (Recommended)
```bash
# Run tests in an ephemeral container (automatically removed on completion)
docker compose run --rm voice-hub python3 -m unittest discover -s tests -p "test_*.py"

# If the container is already running
docker exec SmartSpeaker-VoiceHub python3 -m unittest discover -s tests -p "test_*.py"
```

### Running Tests in Local Python Environment
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

When implementing new features or bug fixes, please add corresponding test cases under `tests/` whenever feasible.

---

## 6. Pull Request Workflow

1. Fork this repository and create a feature branch for your work (e.g., `feature/cool-new-feature` or `fix/issue-123`).
2. Write clear and informative commit messages (we recommend following the [Conventional Commits](https://www.conventionalcommits.org/) convention: `feat:`, `fix:`, `docs:`, `refactor:`, etc.).
3. Run the test suite and confirm that all tests pass.
4. Submit a Pull Request targeting the upstream `main` branch.
5. In the PR description, summarize your changes and reference any related Issue numbers.

---

## 7. License Agreement

All contributions submitted to this repository (via pull requests or otherwise) are understood to be provided under the terms of the project's [MIT License](LICENSE).
