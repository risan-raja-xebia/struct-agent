# Struct-Agent

A full-fledged Structured Query Agent designed to enable natural language to structured query translation, powered by LLMs and schema-aware engines. Built by Xebia.

## Features
- Translate natural language questions into structured queries (e.g., SQL)
- Schema-aware: understands and leverages database schemas
- Extensible architecture for plugging in different LLMs and schema engines
- Supports multiple database backends
- Modular components for easy customization

## Getting Started

### Prerequisites
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended) or [pip](https://pip.pypa.io/)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/struct-agent.git
   cd struct-agent
   ```
2. **Install dependencies:**
   - With uv:
     ```bash
     uv pip install -e .
     uv pip install -r requirements.txt  # if present
     ```
   - Or with pip:
     ```bash
     pip install -e .
     pip install -r requirements.txt  # if present
     ```
3. **Set up environment variables:**
   - Copy `.env.example` to `.env` and fill in required values (e.g., OpenAI API keys, DB connection strings).

4. **(Optional) Set up the sample database:**
   ```bash
   cd workspace/data
   bash load_db.sh
   ```

## Usage

You can use Struct-Agent as a Python library or extend it for your own applications. Example usage:

```python
from struct_agent import ...  # see src/struct_agent for modules
```

## Project Structure
- `src/struct_agent/` - Core library code
- `tests/` - Unit and integration tests
- `workspace/data/` - Example datasets and database setup scripts
- `notebooks/` - Example Jupyter notebooks

## Contributing

We welcome contributions! To get started:

1. Fork the repository and create your branch from `main`.
2. Install development dependencies:
   ```bash
   uv pip install -e .[dev]
   # or
   pip install -e .[dev]
   ```
3. Run tests:
   ```bash
   pytest
   ```
4. Format code and lint:
   ```bash
   ruff check .
   ```
5. Set up pre-commit hooks (recommended):
   ```bash
   uv pip install pre-commit ruff
   pre-commit install
   ```
   This will automatically run code quality checks before each commit.
6. Submit a pull request with a clear description of your changes.

### Guidelines
- Write clear, concise commit messages
- Add/modify tests for new features or bug fixes
- Follow PEP8 and project coding standards
- Document public APIs and modules

## License

[MIT](LICENSE)

## Authors
- Risan Raja <risan.raja@xebia.com>
- Muni Angothu <muni.angothu@xebia.com>

---

For questions or support, please open an issue or contact the maintainers.
