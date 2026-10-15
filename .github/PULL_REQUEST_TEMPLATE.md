## Description
<!-- Provide a concise description of why this change is made (1-3 sentences). -->

## Type of Change
<!-- Select all that apply according to Conventional Commits: -->
- [ ] `feat`: A new feature
- [ ] `fix`: A bug fix
- [ ] `docs`: Documentation changes
- [ ] `style`: Code style/formatting changes
- [ ] `refactor`: Refactoring without feature/bug fix changes
- [ ] `perf`: Performance improvement
- [ ] `test`: Adding or correcting tests
- [ ] `build`: Build system or dependency changes
- [ ] `ci`: CI/CD configuration and scripts
- [ ] `chore`: Miscellaneous housekeeping tasks

## Related Issue / Ticket
<!-- e.g. Fixes #123, Closes #456, or leave blank if none -->

## Key Changes
<!-- Bullet points of key additions, modifications, or fixes -->
### Added
- 

### Changed
- 

### Fixed
- 

## Pre-Commit Checklist
<!-- Check only what you have actually verified -->
- [ ] Ran backend linter (`ruff check src/ tests/`) and passed with 0 errors
- [ ] Ran typechecker (`mypy src/`) and passed with 0 errors
- [ ] Ran backend test suite (`pytest tests/ -m "not integration"`) and all tests passed
- [ ] Ran frontend linter (`npm run lint` in frontend) and passed
- [ ] Ran frontend tests (`npm test` in frontend) and passed
- [ ] Adheres to Hexagonal Modular Monolith architecture and clean code guidelines
- [ ] Updated relevant documentation (API specs, README, architecture docs)
