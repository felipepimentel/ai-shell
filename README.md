# 🚀 AI Shell: Your Intelligent Command-Line Assistant

Welcome to AI Shell, a cutting-edge command-line interface that brings the power of artificial intelligence to your terminal! 🤖✨

## 🌟 Features

- Natural language command processing
- AI-powered command generation and execution
- Intelligent error handling and resolution
- Interactive UI with rich formatting
- Command history management
- Asynchronous operations for improved performance

## 🛠 Installation

1. Clone this repository:

   ```
   git clone https://github.com/yourusername/ai-shell.git
   cd ai-shell
   ```

2. Install dependencies using Poetry:

   ```
   poetry install
   ```

3. Set up your environment variables:

   ```
   cp .env.example .env
   ```

   Edit the `.env` file with your API keys and preferences.

## 🚀 Usage

Launch AI Shell:

```
poetry run python -m ai_shell
```

Once inside the AI Shell, you can:

- Type natural language commands or questions
- Use 'exit' to quit the shell
- Use 'history' to view command history
- Use 'clear history' to clear the command history

## 🎭 Examples

Let's dive into some real-world examples to see AI Shell in action!

### 1. File Management

**User:** Create a new directory called 'project' and add a Python file named 'main.py' inside it.

**AI Shell:**

````
Sure! I can help you create a new directory and add a Python file inside it. Here are the commands to do that:

```bash
mkdir project
touch project/main.py
````

Shall I execute these commands for you?

```

**User:** Yes, please.

**AI Shell:**
```

Executing: mkdir project
Command executed successfully.

Executing: touch project/main.py
Command executed successfully.

✅ Directory 'project' created and 'main.py' file added successfully!

```

### 2. Git Operations

**User:** Initialize a git repository in the current directory, add all files, and make an initial commit.

**AI Shell:**
```

Certainly! I'll help you initialize a Git repository, add all files, and make an initial commit. Here are the commands:

```bash
git init
git add .
git commit -m "Initial commit"
```

Would you like me to execute these commands?

```

**User:** Go ahead.

**AI Shell:**
```

Executing: git init
Initialized empty Git repository in /path/to/your/directory/.git/

Executing: git add .
Command executed successfully.

Executing: git commit -m "Initial commit"
[master (root-commit) f7d2a3c] Initial commit
3 files changed, 45 insertions(+)
create mode 100644 .gitignore
create mode 100644 project/main.py
create mode 100644 README.md

✅ Git repository initialized, files added, and initial commit created successfully!

```

### 3. Python Package Management

**User:** Install the 'requests' library using pip and create a simple script to fetch a webpage.

**AI Shell:**
```

Certainly! I'll help you install the 'requests' library and create a simple script to fetch a webpage. Here's what we'll do:

1. Install the 'requests' library
2. Create a Python script to fetch a webpage

Here are the commands:

```bash
pip install requests
echo "import requests

url = 'https://example.com'
response = requests.get(url)
print(f'Status code: {response.status_code}')
print(f'Content length: {len(response.text)} characters')" > fetch_webpage.py
```

Shall I proceed with these commands?

```

**User:** Yes, please execute them.

**AI Shell:**
```

Executing: pip install requests
Collecting requests
Downloading requests-2.26.0-py2.py3-none-any.whl (62 kB)
|████████████████████████████████| 62 kB 1.2 MB/s
Installing collected packages: requests
Successfully installed requests-2.26.0

Executing: echo "import requests..." > fetch_webpage.py
Command executed successfully.

✅ 'requests' library installed and 'fetch_webpage.py' script created!

Would you like to run the script to test it?

```

**User:** Yes, let's run it.

**AI Shell:**
```

Certainly! I'll run the script for you.

Executing: python fetch_webpage.py
Status code: 200
Content length: 1256 characters

✅ The script ran successfully! It fetched the webpage from example.com and displayed the status code and content length.

```

### 4. Error Handling

**User:** Let's try to remove a non-existent file called 'ghost.txt'.

**AI Shell:**
```

I understand you want to remove a file named 'ghost.txt'. However, this file might not exist. Let's try the command and see what happens:

```bash
rm ghost.txt
```

Shall I execute this command?

```

**User:** Yes, go ahead.

**AI Shell:**
```

Executing: rm ghost.txt
rm: cannot remove 'ghost.txt': No such file or directory

🚨 Error: The file 'ghost.txt' doesn't exist. Would you like me to suggest some options?

1. Check if the file exists in the current directory
2. Search for the file in subdirectories
3. Create the file and then remove it
4. Skip this operation

Which option would you prefer? (Enter the number)

```

**User:** Let's go with option 1.

**AI Shell:**
```

Certainly! I'll check if the file exists in the current directory.

Executing: ls | grep ghost.txt
Command executed successfully, but no output was returned.

It seems that 'ghost.txt' indeed doesn't exist in the current directory. Here's a summary of files in the current directory:

Executing: ls
project/
fetch_webpage.py
README.md
.gitignore

Would you like to do anything else regarding this file?

```

## 🧠 How It Works

AI Shell leverages the power of large language models to interpret your commands, generate appropriate responses, and execute them safely. The main components work together to provide a seamless experience:

- **CLI (cli.py)**: Initializes the UI and AI components, processes command-line arguments, and manages the main loop.
- **UI Handler (ui_handler.py)**: Provides a rich, interactive command-line experience with colorful output and progress indicators.
- **AI Shell Core (ai_shell.py)**: Processes user commands through AI, executes generated commands, and handles errors intelligently.

## 🛡 Security

AI Shell prioritizes your safety:
- Commands are displayed for your approval before execution
- You can edit suggested commands before running them
- The AI model doesn't have direct access to your system

## 🤝 Contributing

We welcome contributions! Please check out our [Contributing Guide](CONTRIBUTING.md) for details on how to get started.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- OpenAI for their groundbreaking language models
- The Rich library for beautiful terminal formatting
- AsyncIO for enabling responsive asynchronous operations

---

Built with ❤️ by the AI Shell team. Happy commanding! 🚀
```
