# Changelog

## [2.1.0] - 2025-08-12

### Changed
- Refactored the backend configuration to centralize the `AI_BASE_DIR`.
- The `AI_BASE_DIR` now defaults to `nexza_data` in the project root if not set as an environment variable.
- Implemented persona selection based on the client interface (Twilio, Discord, iOS).
- Added response cleaning to remove debug traces and meta-phrases from user-facing output.
- Updated the Discord bot to identify itself to the backend using a query parameter.

### Added
- `backend/.env.example` file to document environment variables.
