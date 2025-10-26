# Changelog

All notable changes to TheOpenMusicBox will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- (Add new features here)

### Changed
- (Add changes to existing functionality here)

### Fixed
- (Add bug fixes here)

## [0.4.1] - 2025-10-26

### Added
- Version management system with centralized VERSION file
- `bump_version.sh` script for easy version updates
- CHANGELOG.md for tracking release notes
- Automatic version reading in backend (`app.__version__`)

### Changed
- Unified version management across frontend and backend

### Infrastructure
- Comprehensive deployment system with `deploy.sh`
- Automated testing (78+ backend tests, frontend unit tests)
- Contract validation for API and Socket.IO

## Previous Releases

### [0.4.0] - 2025-09-26
- Initial public beta release
- Core music playback functionality
- NFC tag support
- Web interface
- REST API and WebSocket support
