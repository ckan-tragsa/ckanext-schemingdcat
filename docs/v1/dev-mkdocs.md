## Using MkDocs

This `README.md` provides basic instructions for setting up and using [MkDocs](https://squidfunk.github.io/mkdocs-material/reference/) to generate documentation.

---

### Prerequisites

- Python 3.6 or higher
- pip (Python package manager)

### Installation

**Clone the repository:**

```sh
git clone https://github.com/your-username/your-repository.git
cd your-repository
```

**Create and activate a virtual environment:**

*On Linux/macOS:*

```sh
python3 -m venv venv
source venv/bin/activate
```

*On Windows:*

```command
python -m venv venv
venv\Scripts\activate
```

**Install MkDocs and the Material theme:**

```sh
pip install mkdocs mkdocs-material pymdown-extensions
```

### Project Structure

Ensure your project has the following structure:

```
your-repository/
├── docs/
│   ├── index.md
│   ├── ... (other Markdown files)
├── mkdocs.yml
└── README.md
```

- **docs/**: Folder containing the Markdown files for the documentation.
- **mkdocs.yml**: MkDocs configuration file.
- **README.md**: This file.

### MkDocs Configuration

Example `mkdocs.yml` file:

```yaml
site_name: "Site Name"
theme:
  name: "material"

nav:
  - Home: index.md
  - Page 1: page1.md
  - Page 2: page2.md

markdown_extensions:
  - toc:
      permalink: true
  - admonition
  - pymdownx.highlight
  - pymdownx.inlinehilite
  - pymdownx.superfences
  - pymdownx.tabbed
  - pymdownx.snippets
```

### Generate and Serve Documentation

1. **Navigate to the project directory:**

   ```sh
   cd your-repository
   ```

2. **Start the development server:**

   ```sh
   mkdocs serve -a 127.0.0.1:8088
   ```

3. **Open your browser and navigate to:**

   ```
   http://127.0.0.1:8088
   ```

### Build Documentation for Production

To generate the static files for the documentation:

```sh
mkdocs build
```

The generated files will be located in the `site/` folder.

### Debug MkDocs

To debug MkDocs, follow these steps:

```sh
cd ckanext-schemingdcat
mkdocs serve -a 127.0.0.1:8088
```

### Additional Resources

- [MkDocs Official Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)

---
