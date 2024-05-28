import os
import re
from rich.console import Console
from rich.panel import Panel
from datetime import datetime
import json
from litellm import completion
from tavily import TavilyClient

# Set environment variables for API keys for the services you are using
os.environ["OPENAI_API_KEY"] = "YOUR OPENAI API KEY"
os.environ["ANTHROPIC_API_KEY"] = "YOUR ANTHROPIC API KEY"
os.environ["GEMINI_API_KEY"] = "YOUR GEMINI API KEY"

# Define the models to be used for each stage
ORCHESTRATOR_MODEL = "gemini/gemini-1.5-flash-latest"
SUB_AGENT_MODEL = "gemini/gemini-1.5-flash-latest"
REFINER_MODEL = "gemini/gemini-1.5-flash-latest"

# Initialize the Rich Console
console = Console()

def gpt_orchestrator(objective, file_content=None, previous_results=None, use_search=False):
    console.print(f"\n[bold]Calling Orchestrator for your objective[/bold]")
    previous_results_text = "\n".join(previous_results) if previous_results else "None"
    if file_content:
        console.print(Panel(f"File content:\n{file_content}", title="[bold blue]File Content[/bold blue]", title_align="left", border_style="blue"))
    
    messages = [
        {"role": "system", "content": "You are a detailed and meticulous assistant. Your primary goal is to break down complex objectives into manageable sub-tasks, provide thorough reasoning, and ensure code correctness. Always explain your thought process step-by-step and validate any code for errors, improvements, and adherence to best practices."},
        {"role": "user", "content": f"Based on the following objective{' and file content' if file_content else ''}, and the previous sub-task results (if any), please break down the objective into the next sub-task, and create a concise and detailed prompt for a subagent so it can execute that task. IMPORTANT!!! when dealing with code tasks make sure you check the code for errors and provide fixes and support as part of the next sub-task. If you find any bugs or have suggestions for better code, please include them in the next sub-task prompt. Please assess if the objective has been fully achieved. If the previous sub-task results comprehensively address all aspects of the objective, include the phrase 'The task is complete:' at the beginning of your response. If the objective is not yet fully achieved, break it down into the next sub-task and create a concise and detailed prompt for a subagent to execute that task.:\n\nObjective: {objective}" + ('\nFile content:\n' + file_content if file_content else '') + f"\n\nPrevious sub-task results:\n{previous_results_text}"}
    ]

    if use_search:
        messages.append({"role": "user", "content": "Please also generate a JSON object containing a single 'search_query' key, which represents a question that, when asked online, would yield important information for solving the subtask. The question should be specific and targeted to elicit the most relevant and helpful resources. Format your JSON like this, with no additional text before or after:\n{\"search_query\": \"<question>\"}\n"})

    response = completion(model=ORCHESTRATOR_MODEL, messages=messages)

    response_text = response['choices'][0]['message']['content']

    console.print(Panel(response_text, title=f"[bold green]Orchestrator[/bold green]", title_align="left", border_style="green", subtitle="Sending task to sub-agent 👇"))

    search_query = None
    if use_search:
        json_match = re.search(r'{.*}', response_text, re.DOTALL)
        if json_match:
            json_string = json_match.group()
            try:
                search_query = json.loads(json_string)["search_query"]
                console.print(Panel(f"Search Query: {search_query}", title="[bold blue]Search Query[/bold blue]", title_align="left", border_style="blue"))
                response_text = response_text.replace(json_string, "").strip()
            except json.JSONDecodeError as e:
                console.print(Panel(f"Error parsing JSON: {e}", title="[bold red]JSON Parsing Error[/bold red]", title_align="left", border_style="red"))
                console.print(Panel(f"Skipping search query extraction.", title="[bold yellow]Search Query Extraction Skipped[/bold yellow]", title_align="left", border_style="yellow"))
        else:
            search_query = None

    return response_text, file_content, search_query

def gpt_sub_agent(prompt, search_query=None, previous_gpt_tasks=None, use_search=False, continuation=False):
    if previous_gpt_tasks is None:
        previous_gpt_tasks = []

    continuation_prompt = "Continuing from the previous answer, please complete the response."
    system_message = (
        "You are an expert assistant. Your goal is to execute tasks accurately, provide detailed explanations of your reasoning, "
        "and ensure the correctness and quality of any code. Always explain your thought process and validate your output thoroughly.\n\n"
        "Previous tasks:\n" + "\n".join(f"Task: {task['task']}\nResult: {task['result']}" for task in previous_gpt_tasks)
    )
    if continuation:
        prompt = continuation_prompt

    qna_response = None
    if search_query and use_search:
        tavily = TavilyClient(api_key="your-tavily-key")
        qna_response = tavily.qna_search(query=search_query)
        console.print(f"QnA response: {qna_response}", style="yellow")

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]

    if qna_response:
        messages.append({"role": "user", "content": f"\nSearch Results:\n{qna_response}"})

    response = completion(model=SUB_AGENT_MODEL, messages=messages)

    response_text = response['choices'][0]['message']['content']

    console.print(Panel(response_text, title="[bold blue]Sub-agent Result[/bold blue]", title_align="left", border_style="blue", subtitle="Task completed, sending result to Orchestrator 👇"))

    if len(response_text) >= 4000:  # Threshold set to 4000 as a precaution
        console.print("[bold yellow]Warning:[/bold yellow] Output may be truncated. Attempting to continue the response.")
        continuation_response_text = gpt_sub_agent(prompt, search_query, previous_gpt_tasks, use_search, continuation=True)
        response_text += continuation_response_text

    return response_text

def anthropic_refine(objective, sub_task_results, filename, projectname, continuation=False):
    console.print("\nCalling Opus to provide the refined final output for your objective:")
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Objective: " + objective + "\n\nSub-task results:\n" + "\n".join(sub_task_results) + "\n\nPlease review and refine the sub-task results into a cohesive final output. Add any missing information or details as needed. When working on code projects, ONLY AND ONLY IF THE PROJECT IS CLEARLY A CODING ONE please provide the following:\n1. Project Name: Create a concise and appropriate project name that fits the project based on what it's creating. The project name should be no more than 20 characters long.\n2. Folder Structure: Provide the folder structure as a valid JSON object, where each key represents a folder or file, and nested keys represent subfolders. Use null values for files. Ensure the JSON is properly formatted without any syntax errors. Please make sure all keys are enclosed in double quotes, and ensure objects are correctly encapsulated with braces, separating items with commas as necessary.\nWrap the JSON object in <folder_structure> tags.\n3. Code Files: For each code file, include ONLY the file name NEVER EVER USE THE FILE PATH OR ANY OTHER FORMATTING YOU ONLY USE THE FOLLOWING format 'Filename: <filename>' followed by the code block enclosed in triple backticks, with the language identifier after the opening backticks, like this:\n\n```python\n<code>\n```"}
            ]
        }
    ]

    response = completion(model=REFINER_MODEL, messages=messages)

    response_text = response['choices'][0]['message']['content']
    console.print(Panel(response_text, title="[bold green]Final Output[/bold green]", title_align="left", border_style="green"))

    if len(response_text) >= 4000 and not continuation:  # Threshold set to 4000 as a precaution
        console.print("[bold yellow]Warning:[/bold yellow] Output may be truncated. Attempting to continue the response.")
        continuation_response_text = anthropic_refine(objective, sub_task_results + [response_text], filename, projectname, continuation=True)
        response_text += "\n" + continuation_response_text

    return response_text

def create_folder_structure(project_name, folder_structure, code_blocks):
    try:
        os.makedirs(project_name, exist_ok=True)
        console.print(Panel(f"Created project folder: [bold]{project_name}[/bold]", title="[bold green]Project Folder[/bold green]", title_align="left", border_style="green"))
    except OSError as e:
        console.print(Panel(f"Error creating project folder: [bold]{project_name}[/bold]\nError: {e}", title="[bold red]Project Folder Creation Error[/bold red]", title_align="left", border_style="red"))
        return

    create_folders_and_files(project_name, folder_structure, code_blocks)

def create_folders_and_files(current_path, structure, code_blocks):
    for key, value in structure.items():
        path = os.path.join(current_path, key)
        if isinstance(value, dict):
            try:
                os.makedirs(path, exist_ok=True)
                console.print(Panel(f"Created folder: [bold]{path}[/bold]", title="[bold blue]Folder Creation[/bold blue]", title_align="left", border_style="blue"))
                create_folders_and_files(path, value, code_blocks)
            except OSError as e:
                console.print(Panel(f"Error creating folder: [bold]{path}[/bold]\nError: {e}", title="[bold red]Folder Creation Error[/bold red]", title_align="left", border_style="red"))
        else:
            code_content = next((code for file, code in code_blocks if file == key), None)
            if code_content:
                try:
                    with open(path, 'w') as file:
                        file.write(code_content)
                    console.print(Panel(f"Created file: [bold]{path}[/bold]", title="[bold green]File Creation[/bold green]", title_align="left", border_style="green"))
                except IOError as e:
                    console.print(Panel(f"Error creating file: [bold]{path}[/bold]\nError: {e}", title="[bold red]File Creation Error[/bold red]", title_align="left", border_style="red"))
            else:
                console.print(Panel(f"Code content not found for file: [bold]{key}[/bold]", title="[bold yellow]Missing Code Content[/bold yellow]", title_align="left", border_style="yellow"))

def read_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    return content

# Get the objective from user input
objective = input("Please enter your objective: ")

# Ask the user if they want to provide a file path
provide_file = input("Do you want to provide a file path? (y/n): ").lower() == 'y'

if provide_file:
    file_path = input("Please enter the file path: ")
    if os.path.exists(file_path):
        file_content = read_file(file_path)
    else:
        print(f"File not found: {file_path}")
        file_content = None
else:
    file_content = None

# Ask the user if they want to use search
use_search = input("Do you want to use search? (y/n): ").lower() == 'y'

task_exchanges = []
gpt_tasks = []

while True:
    previous_results = [result for _, result in task_exchanges]
    if not task_exchanges:
        gpt_result, file_content_for_gpt, search_query = gpt_orchestrator(objective, file_content, previous_results, use_search)
    else:
        gpt_result, _, search_query = gpt_orchestrator(objective, previous_results=previous_results, use_search=use_search)

    if "The task is complete:" in gpt_result:
        final_output = gpt_result.replace("The task is complete:", "").strip()
        break
    else:
        sub_task_prompt = gpt_result
        if file_content_for_gpt and not gpt_tasks:
            sub_task_prompt = f"{sub_task_prompt}\n\nFile content:\n{file_content_for_gpt}"
        sub_task_result = gpt_sub_agent(sub_task_prompt, search_query, gpt_tasks, use_search)
        gpt_tasks.append({"task": sub_task_prompt, "result": sub_task_result})
        task_exchanges.append((sub_task_prompt, sub_task_result))
        file_content_for_gpt = None

# Include both orchestrator prompts and sub-agent results in sub-task results
sub_task_results = [f"Orchestrator Prompt: {prompt}\nSub-agent Result: {result}" for prompt, result in task_exchanges]

sanitized_objective = re.sub(r'\W+', '_', objective)
timestamp = datetime.now().strftime("%H-%M-%S")
refined_output = anthropic_refine(objective, sub_task_results, timestamp, sanitized_objective)

project_name_match = re.search(r'Project Name: (.*)', refined_output)
project_name = project_name_match.group(1).strip() if project_name_match else sanitized_objective

folder_structure_match = re.search(r'<folder_structure>(.*?)</folder_structure>', refined_output, re.DOTALL)
folder_structure = {}
if folder_structure_match:
    json_string = folder_structure_match.group(1).strip()
    try:
        folder_structure = json.loads(json_string)
    except json.JSONDecodeError as e:
        console.print(Panel(f"Error parsing JSON: {e}", title="[bold red]JSON Parsing Error[/bold red]", title_align="left", border_style="red"))
        console.print(Panel(f"Invalid JSON string: [bold]{json_string}[/bold]", title="[bold red]Invalid JSON String[/bold red]", title_align="left", border_style="red"))

# Ensure proper extraction of filenames and code contents
code_blocks = re.findall(r'Filename: (\S+)\s*```[\w]*\n(.*?)\n```', refined_output, re.DOTALL)
create_folder_structure(project_name, folder_structure, code_blocks)

max_length = 25
truncated_objective = sanitized_objective[:max_length] if len(sanitized_objective) > max_length else sanitized_objective

filename = f"{timestamp}_{truncated_objective}.md"

exchange_log = f"Objective: {objective}\n\n"
exchange_log += "=" * 40 + " Task Breakdown " + "=" * 40 + "\n\n"
for i, (prompt, result) in enumerate(task_exchanges, start=1):
    exchange_log += f"Task {i}:\n"
    exchange_log += f"Prompt: {prompt}\n"
    exchange_log += f"Result: {result}\n\n"

exchange_log += "=" * 40 + " Refined Final Output " + "=" * 40 + "\n\n"
exchange_log += refined_output

console.print(f"\n[bold]Refined Final output:[/bold]\n{refined_output}")

with open(filename, 'w') as file:
    file.write(exchange_log)
print(f"\nFull exchange log saved to {filename}")

