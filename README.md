# Maestro - A Framework for Claude Opus, GPT and local LLMs to Orchestrate Subagents


This Python script demonstrates an AI-assisted task breakdown and execution workflow using the Anthropic API. It utilizes two AI models, Opus and Haiku, to break down an objective into sub-tasks, execute each sub-task, and refine the results into a cohesive final output.

## New: 
# Updated the original Maestro to support Claude 3.5 Sonnet
```bash
python maestro.py
```


# Use Maestro with any APIs, Anthropic, Gemini, OpenAI, Cohere, etc.
Thanks to a rewrite of the codebase using LiteLLM, it's now much easier to select the model you want.

Simply
#### Set environment variables for API keys for the services you are using
os.environ["OPENAI_API_KEY"] = "YOUR KEY" 

os.environ["ANTHROPIC_API_KEY"] = "YOUR KEY"

os.environ["GEMINI_API_KEY"] = "YOUR KEY"

#### Define the models to be used for each stage
ORCHESTRATOR_MODEL = "gemini/gemini-1.5-flash-latest"

SUB_AGENT_MODEL = "gemini/gemini-1.5-flash-latest"

REFINER_MODEL = "gemini/gemini-1.5-flash-latest"

Or gpt-3.5-turbo, etc.

First install litellm
```bash
pip install litellm
```

Afeter installing dependecies run

```bash
python maestro-anyapi.py
```


## GPT-4o

The GPT script has been updated from the ground up to support the code capabilities of GPT-4o

Afeter installing dependecies run

```bash
python maestro-gpt4o.py
```

## Run locally with LMStudio or Ollama

### Lmstudio

First download the app here
https://lmstudio.ai/

Then run the local server using your preferred method. I also recommend removing any system prompt for the app (leave your prompt field empty so it can take advantage of the script prompts).

Then
```bash
python maestro-lmstudio.py
```


### Ollama
Mestro now runs locally thanks to the Ollama platform. Experience the power of Llama 3 locally! 

Before running the script

Install Ollama client from here
https://ollama.com/download

then

```bash
pip install ollama
```
And 

```bash
ollama.pull('llama3:70b')
```
This will depend on the model you want to use it, you only need to do it once or if you want to update the model when a new version it's out.
In the script I am using both versions but you can customize the model you want to use

ollama.pull('llama3:70b')
ollama.pull('llama3:8b')

Then

```bash
python maestro-ollama.py
```

## Highly requested features
- GROQ SUPPORT
Experience the power of maestro thanks to Groq super fast api responses.
```bash
pip install groq
```
Then

```bash
python maestro-groq.py
```


- SEARCH 🔍

Now, when it's creating a task for its subagent, Claude Opus will perform a search and get the best answer to help the subagent solve that task even better.

Make sure you replace your Tavil API for search to work

Get one here https://tavily.com/
  
- GPT4 SUPPORT

Add support for GPT-4 as an orchestrator in maestro-gpt.py
Simply
```bash
python maestro-gpt.py
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
- Creates code files and folders when working on code projects.

## Prerequisites

To run this script, you need to have the following:

- Python installed
- Anthropic API key
- Required Python packages: `anthropic` and `rich`

## Installation

1. Clone the repository or download the script file.
2. Install the required Python packages by running the following command:

```bash
pip install -r requirements.txt
```

3. Replace the placeholder API key in the script with your actual Anthropic API key:

```python
client = Anthropic(api_key="YOUR_API_KEY_HERE")
```

If using search, replace your Tavil API
```python
tavily = TavilyClient(api_key="YOUR API KEY HERE")
```

## Usage

1. Open a terminal or command prompt and navigate to the directory containing the script.
2. Run the script using the following command:

```bash
python maestro.py
```

3. Enter your objective when prompted:

```bash
Please enter your objective: Your objective here
```

The script will start the task breakdown and execution process. It will display the progress and results in the console using formatted panels.

Once the process is complete, the script will display the refined final output and save the full exchange log to a Markdown file with a filename based on the objective.

## Code Structure

The script consists of the following main functions:

- `opus_orchestrator(objective, previous_results=None)`: Calls the Opus model to break down the objective into sub-tasks or provide the final output. It uses an improved prompt to assess task completion and includes the phrase "The task is complete:" when the objective is fully achieved.
- `haiku_sub_agent(prompt, previous_haiku_tasks=None)`: Calls the Haiku model to execute a sub-task prompt, providing it with the memory of previous sub-tasks.
- `opus_refine(objective, sub_task_results)`: Calls the Opus model to review and refine the sub-task results into a cohesive final output.

The script follows an iterative process, repeatedly calling the opus_orchestrator function to break down the objective into sub-tasks until the final output is provided. Each sub-task is then executed by the haiku_sub_agent function, and the results are stored in the task_exchanges and haiku_tasks lists.

The loop terminates when the Opus model includes the phrase "The task is complete:" in its response, indicating that the objective has been fully achieved.

Finally, the opus_refine function is called to review and refine the sub-task results into a final output. The entire exchange log, including the objective, task breakdown, and refined final output, is saved to a Markdown file.

## Customization

You can customize the script according to your needs:

- Adjust the max_tokens parameter in the client.messages.create() function calls to control the maximum number of tokens generated by the AI models.
- Change the models to what you prefer, like replacing Haiku with Sonnet or Opus.
- Modify the console output formatting by updating the rich library's Panel and Console configurations.
- Customize the exchange log formatting and file extension by modifying the relevant code sections.

## License

This script is released under the MIT License.

## Acknowledgements

- Anthropic for providing the AI models and API.
- Rich for the beautiful console formatting.

## Flask App Integration

We have now integrated a Flask app to provide a user-friendly interface for interacting with the Maestro framework. This addition allows users to input objectives and view results through a web interface, enhancing the overall usability of the tool.

### Setting Up and Running the Flask App

To set up and run the Flask app, follow these steps:

1. Ensure Flask is installed by running `pip install Flask` or by adding Flask to the `requirements.txt` file and running `pip install -r requirements.txt`.
2. Navigate to the directory containing the Flask app files (`app.py`, `templates/`, and `static/`).
3. Run the Flask app by executing `python app.py` in your terminal or command prompt.
4. Access the web interface by opening a web browser and navigating to `http://localhost:5000/`.

The Flask app supports all features of the Maestro framework, allowing users to input objectives and view the orchestrated task breakdown and execution results in a structured and easy-to-read format.

### UI Features

The Flask app includes the following UI features:

- A form for inputting objectives.
- A results display area where the orchestrated task breakdown and execution results are shown.
- Basic styling for improved readability and user experience.

This integration aims to make the Maestro framework more accessible and user-friendly, providing an intuitive way for users to leverage the power of AI-assisted task breakdown and execution.

### Updated Instructions for Running the Flask App

To run the Flask app with the updated file structure, follow these steps:

1. Navigate to the `flask_app` directory.
2. Execute `python app.py` to start the Flask server.
3. Access the web interface by navigating to `http://localhost:5000/` in your web browser.

This update ensures that all Flask app-related files are neatly organized within the `flask_app` folder, simplifying the project structure and making it easier to manage.
