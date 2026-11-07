# Contributing to Wi-Fi Heartbeat Tracker

Thank you for your interest in contributing to Wi-Fi Heartbeat Tracker!

## Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/<your-username>/wifi-heartbeat-tracker.git
   cd wifi-heartbeat-tracker
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux / macOS:
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running Tests & Benchmarks

Before submitting any code changes, ensure all tests and benchmarks pass:

- **Run all unit tests:**
  ```bash
  pytest
  ```

- **Run simulator accuracy benchmark:**
  ```bash
  python benchmark.py --trials 30
  ```

## Code Guidelines

- **Safety and Reliability First:** The system follows the rule: *never show a wrong BPM; rejecting unreliable readings is acceptable.* Any modification to the pipeline or quality gates must not increase false acceptance rates.
- **Signal Processing Integrity:** Preserve physiological constraints (e.g., heart band 42–132 BPM, breathing band 6–30 bpm).
- **Hardware Abstraction:** Real hardware drivers should implement `HardwareCSISource` in `acquisition/csi_loader.py`.
- **Typing & Formatting:** Use type annotations (`from __future__ import annotations`) and keep imports clean.

## Submitting Pull Requests

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Commit your changes with clear messages.
3. Push to your fork: `git push origin feature/my-feature`
4. Open a Pull Request detailing the changes and benchmark results.
