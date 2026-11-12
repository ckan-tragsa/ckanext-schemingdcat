## Development
### Update Internationalization (i18n) Files
To compile a `.po` file to a `.mo` file in the terminal, you can use the `msgfmt` tool, which is part of the `gettext` package. Here are the steps to do it:

### Steps to Compile `.po` File to `.mo` File.

1. **Install `gettext` (if not already installed)**:
   - On most Linux distributions, you can install `gettext` using your system's package manager. For example, in Debian/Ubuntu:

   ```sh
   sudo apt-get install gettext
   ```

   In Fedora:

   ````sh
   sudo dnf install gettext
   ```

2. **Compile the `.po` file to `.mo`**:
   - Use the `msgfmt` command to compile the `.po` file to `.mo`. **Make sure you are in the directory where your `.po` file is located or provide the full path to the file.**

   ```sh
   msgfmt -o ckanext-schemingdcat.mo ckanext-schemingdcat.po
   ```

   - This command will generate a `ckanext-schemingdcat.mo` file in the same directory as the `.po` file.

### Complete Example

Let's assume your `.po` file is located in the `i18n/en/LC_MESSAGES/` directory inside your project. Here are the complete commands:

1. 1. **Navigate to the Project Directory**:

   ```sh
   cd /path/to/your/project
   ```

2. **Navigate to the Directory Containing the `.po`** File:

   ```sh
   cd i18n/en/LC_MESSAGES/
   ```

3. **Compile the `.po` file to `.mo`**:

   ```sh
   msgfmt -o ckanext-schemingdcat.mo ckanext-schemingdcat.po
   ```

### Verification

1. Verify that the `.mo` file has been generated in the browser.