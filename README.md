# Maestro - A Framework for Claude Opus, GPT, and Local LLMs to Orchestrate Subagents

This Python script demonstrates an AI-assisted task breakdown and execution workflow using the Anthropic API. It utilizes two AI models, Opus and Haiku, to break down an objective into sub-tasks, execute each sub-task, and refine the results into a cohesive final output.

## New:

### GPT-4o

The GPT script has been updated from the ground up to support the code capabilities of GPT-4o.

After installing dependencies, run:

```bash
poetry run python maestro-gpt4o.py
```

## Run Locally with LMStudio or Ollama

### LMStudio

First, download the app [here](https://lmstudio.ai/).

Then run the local server using your preferred method. I also recommend removing any system prompt for the app (leave your prompt field empty so it can take advantage of the script prompts).

Then:

```bash
poetry run python maestro-lmstudio.py
```

### Ollama

Maestro now runs locally thanks to the Ollama platform. Experience the power of Llama 3 locally!

Before running the script, install the Ollama client from [here](https://ollama.com/download).

Then:

```bash
poetry add ollama
```

And:

```bash
ollama pull llama3:70b
```

This will depend on the model you want to use; you only need to do it once or if you want to update the model when a new version is out. In the script, I am using both versions, but you can customize the model you want to use:

```bash
ollama pull llama3:70b
ollama pull llama3:8b
```

Then:

```bash
poetry run python maestro-ollama.py
```

## Highly Requested Features

### GROQ Support

Experience the power of Maestro thanks to Groq's super-fast API responses.

```bash
poetry add groq
```

Then:

```bash
poetry run python maestro-groq.py
```

### Search 🔍

Now, when creating a task for its subagent, Claude Opus will perform a search and get the best answer to help the subagent solve that task even better.

Make sure you replace your Tavil API key for search to work. Get one [here](https://tavily.com/).

### GPT-4 Support

Add support for GPT-4 as an orchestrator in maestro-gpt.py. Simply:

```bash
poetry run python maestro-gpt.py
```

After you complete your installs.

## Features

- Breaks down an objective into manageable sub-tasks using the Opus model
- Executes each sub-task using the Haiku model
- Provides the Haiku model with memory of previous sub-tasks for context
- Refines the sub-task results into a final output using the Opus model
- Generates a detailed exchange log capturing the entire task breakdown and execution process
- Saves the exchange log to a Markdown file for easy reference
- Utilizes an improved prompt for the Opus model to better assess task completion
- Creates code files and folders when working on code projects

## Prerequisites

To run this script, you need to have the following:

- Python installed
- Anthropic API key
- Required Python packages

## Installation

1. Clone the repository or download the script file.
2. Install Poetry if you haven't already:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. Install the required Python packages by running the following command:

```bash
poetry install
```

4. Create a `.env` file in the root directory of your project and add your API keys:

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
OPENAI_API_KEY=your_openai_api_key
GROQ_API_KEY=your_groq_api_key
```

## Usage

1. Open a terminal or command prompt and navigate to the directory containing the script.
2. Run the script using the following command:

```bash
poetry run python maestro.py
```

3. Enter your objective when prompted:

```bash
Please enter your objective: Your objective here
```

The script will start the task breakdown and execution process. It will display the progress and results in the console using formatted panels.

Once the process is complete, the script will display the refined final output and save the full exchange log to a Markdown file in a local folder named `./objectives/{time}`, where `{time}` is the current timestamp.

## Code Structure

The script consists of the following main functions:

- `opus_orchestrator(objective, previous_results=None)`: Calls the Opus model to break down the objective into sub-tasks or provide the final output. It uses an improved prompt to assess task completion and includes the phrase "The task is complete:" when the objective is fully achieved.
- `haiku_sub_agent(prompt, previous_haiku_tasks=None)`: Calls the Haiku model to execute a sub-task prompt, providing it with the memory of previous sub-tasks.
- `opus_refine(objective, sub_task_results)`: Calls the Opus model to review and refine the sub-task results into a cohesive final output.

The script follows an iterative process, repeatedly calling the `opus_orchestrator` function to break down the objective into sub-tasks until the final output is provided. Each sub-task is then executed by the `haiku_sub_agent` function, and the results are stored in the `task_exchanges` and `haiku_tasks` lists.

The loop terminates when the Opus model includes the phrase "The task is complete:" in its response, indicating that the objective has been fully achieved.

Finally, the `opus_refine` function is called to review and refine the sub-task results into a final output. The entire exchange log, including the objective, task breakdown, and refined final output, is saved to a Markdown file in a local folder named `./objectives/{time}`, where `{time}` is the current timestamp.

## Customization

You can customize the script according to your needs:

- Adjust the `max_tokens` parameter in the `client.messages.create()` function calls to control the maximum number of tokens generated by the AI models.
- Change the models to what you prefer, like replacing Haiku with Sonnet or Opus.
- Modify the console output formatting by updating the `rich` library's `Panel` and `Console` configurations.
- Customize the exchange log formatting and file extension by modifying the relevant code sections.

## License

This script is released under the MIT License.

## Acknowledgements

- Anthropic for providing the AI models and API.
- Rich for the beautiful console formatting.
