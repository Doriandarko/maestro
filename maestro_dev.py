
## TO ADD: LITELLM SUPPORT FOR EASY SWITCHING MODELS/PROVIDERS. + UPDATE OLLAMA AND LMSTUDIO SCRIPTS

import os
from anthropic import Anthropic
import re
from rich.console import Console
from rich.panel import Panel
from datetime import datetime
import json
from tavily import TavilyClient
import dotenv
from e2b_code_interpreter import CodeInterpreter, Result
from e2b_code_interpreter.models import Logs
from typing import Tuple, List

dotenv.load_dotenv()

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY') 
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Available Claude models:
# Claude 3 Opus	    claude-3-opus-20240229
# Claude 3 Sonnet	claude-3-sonnet-20240229
# Claude 3 Haiku	claude-3-haiku-20240307

ORCHESTRATOR_MODEL = "claude-3-opus-20240229"
SUB_AGENT_MODEL = "claude-3-sonnet-20240229" 
REFINER_MODEL = "claude-3-opus-20240229"

def calculate_subagent_cost(model, input_tokens, output_tokens):
    # Pricing information per model
    pricing = {
        "claude-3-opus-20240229": {"input_cost_per_mtok": 15.00, "output_cost_per_mtok": 75.00},
        "claude-3-haiku-20240307": {"input_cost_per_mtok": 0.25, "output_cost_per_mtok": 1.25},
        "claude-3-sonnet-20240229": {"input_cost_per_mtok": 3.00, "output_cost_per_mtok": 15.00},
    }

    # Calculate cost
    input_cost = (input_tokens / 1_000_000) * pricing[model]["input_cost_per_mtok"]
    output_cost = (output_tokens / 1_000_000) * pricing[model]["output_cost_per_mtok"]
    total_cost = input_cost + output_cost

    return total_cost

console = Console()



def opus_orchestrator(objective, file_content=None, previous_results=None, use_search=False, task_exchanges=None):
    console.print(f"\n[bold]Calling Orchestrator for your objective[/bold]")
    
    # Flatten the previous_results if it's a list of lists
    if previous_results:
        flat_previous_results = [item for sublist in previous_results for item in sublist] if any(isinstance(el, list) for el in previous_results) else previous_results
        previous_results_text = "\n".join(flat_previous_results)
    else:
        previous_results_text = "No previous sub-task results available."

    if file_content:
        console.print(Panel(f"File content:\n{file_content}", title="[bold blue]File Content[/bold blue]", title_align="left", border_style="blue"))
    
    messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": f"Based on the following objective{' and file content' if file_content else ''}, and the previous sub-task results (if any), please provide feedback on the progress made so far and identify any areas that need further improvement. Then, break down the objective into the next sub-task, and create a concise and detailed prompt for a subagent so it can execute that task. And please always make sure your messages are NOT empty. IMPORTANT!!! when dealing with code tasks make sure you check the code for errors and provide fixes and support as part of the next sub-task. If you find any bugs or have suggestions for better code, please include them in the next sub-task prompt. Make sure to remind the sub and coding agents to install necessary packages and import when generating and running code. Please also make sure the subagents provide code to the coding agent properly formatted and structured (for ex, all strings should be marked with # to avoid stupid syntax errors) for the execution. Please assess if the objective has been fully achieved. If the previous sub-task results comprehensively address all aspects of the objective, include the phrase 'The task is complete:' at the beginning of your response. If the objective is not yet fully achieved, break it down into the next sub-task and create a concise and detailed prompt for a subagent to execute that task.:\n\nObjective: {objective}" + ('\\nFile content:\\n' + file_content if file_content else '') + f"\n\nPrevious sub-task results:\n{previous_results_text}"}
        ]
    }
]
    
    if use_search:
        messages[0]["content"].append({"type": "text", "text": "Please also generate a JSON object containing a single 'search_query' key, which represents a question that, when asked online, would yield important information for solving the subtask. The question should be specific and targeted to elicit the most relevant and helpful resources. And please always make sure your messages are NOT empty. Format your JSON like this, with no additional text before or after:\n{\"search_query\": \"<question>\"}\n"})

    # Ensure task_exchanges is passed and used correctly
    if task_exchanges is not None:
        code_files_present = all(re.search(r'Filename: (\S+)\s*```[\w]*\n(.*?)\n```', result, re.DOTALL) for _, result in task_exchanges)

    opus_response = client.messages.create(
        model=ORCHESTRATOR_MODEL,
        max_tokens=4096,
        messages=messages
    )

    response_text = opus_response.content[0].text.strip()

    # Check if the response_text is empty or whitespace
    while not response_text:
        console.print(Panel("Empty response received from the orchestrator. Retrying...", title="[bold yellow]Empty Orchestrator Response[/bold yellow]", title_align="left", border_style="yellow"))
        opus_response = client.messages.create(
            model=ORCHESTRATOR_MODEL,
            max_tokens=4096,
            messages=messages
        )
        response_text = opus_response.content[0].text.strip()

    # Check if the task is complete only if all code files are present and there are no errors
    if "The task is complete:" in response_text:
        code_files_present = all(re.search(r'Filename: (\S+)\s*```[\w]*\n(.*?)\n```', result, re.DOTALL) for _, result in task_exchanges)
        no_errors_in_results = all("Error executing the generated code" not in result for _, result in task_exchanges)

        if code_files_present and no_errors_in_results:
            final_output = response_text.replace("The task is complete:", "").strip()
            console.print(Panel(final_output, title="[bold green]Task Complete[/bold green]", title_align="left", border_style="green"))
            return final_output, None, None
        else:
            console.print(Panel("Code files missing or errors detected. Continuing refinement process.", title="[bold yellow]Refinement Needed[/bold yellow]", title_align="left", border_style="yellow"))
            response_text = response_text.replace("The task is complete:", "").strip()

    # Extract the search query from the response
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

    console.print(Panel(response_text, title=f"[bold green]Opus Orchestrator[/bold green]", title_align="left", border_style="green", subtitle="Sending task to Haiku 👇"))
    return response_text, file_content, search_query

def haiku_sub_agent(prompt, search_query=None, previous_haiku_tasks=None, use_search=False, continuation=False):
    # Check if the sub_task_prompt is empty or whitespace
    if not prompt.strip():
        console.print(Panel("Empty sub-task prompt received. Skipping API call.", title="[bold yellow]Empty Sub-task Prompt[/bold yellow]", title_align="left", border_style="yellow"))
        return "The sub-task prompt is empty. Please provide a valid prompt."
    if previous_haiku_tasks is None:
        previous_haiku_tasks = []

    continuation_prompt = "Continuing from the previous answer, please complete the response."
    system_message = "Previous Haiku tasks:\n" + "\n".join(f"Task: {task['task']}\nResult: {task['result']}" for task in previous_haiku_tasks)
    if continuation:
        prompt = continuation_prompt

    qna_response = None
    if search_query and use_search:
        # Initialize the Tavily client
        tavily = TavilyClient(api_key=TAVILY_API_KEY)
        # Perform a QnA search based on the search query
        qna_response = tavily.qna_search(query=search_query)
        console.print(f"QnA response: {qna_response}", style="yellow")

    # Prepare the messages array with only the prompt initially
    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt}]
        }
    ]

    # Add search results to the messages if there are any
    if qna_response:
        messages[0]["content"].append({"type": "text", "text": f"\nSearch Results:\n{qna_response}"})

    haiku_response = client.messages.create(
        model=SUB_AGENT_MODEL,
        max_tokens=4096,
        messages=messages,
        system=system_message
    )

    response_text = haiku_response.content[0].text
    console.print(f"Input Tokens: {haiku_response.usage.input_tokens}, Output Tokens: {haiku_response.usage.output_tokens}")
    total_cost = calculate_subagent_cost(SUB_AGENT_MODEL, haiku_response.usage.input_tokens, haiku_response.usage.output_tokens)
    console.print(f"Sub-agent Cost: ${total_cost:.4f}")

    if haiku_response.usage.output_tokens >= 4000:  # Threshold set to 4000 as a precaution
        console.print("[bold yellow]Warning:[/bold yellow] Output may be truncated. Attempting to continue the response.")
        continuation_response_text = haiku_sub_agent(prompt, search_query, previous_haiku_tasks, use_search, continuation=True)
        response_text += continuation_response_text

    console.print(Panel(response_text, title="[bold blue]Haiku Sub-agent Result[/bold blue]", title_align="left", border_style="blue", subtitle="Task completed, sending result to Opus 👇"))
    return response_text

def opus_refine(objective, sub_task_results, filename, projectname, continuation=False):
    # Ensure all elements in sub_task_results are strings
    sub_task_results = [str(result) for result in sub_task_results]
    print("\nCalling Opus to provide the refined final output for your objective:")
    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": "Objective: " + objective + "\n\nSub-task results:\n" + "\n".join(sub_task_results) + "\n\nPlease provide detailed feedback on the sub-task results, highlighting any key points, areas for improvement, or insights gained. Then, review and refine the sub-task results into a cohesive final output, adding any missing information or details as needed. If you encounter any issues, such as missing code or errors, please attempt to refine the results to resolve the issues. If you are unable to resolve the issues, please provide a clear description of the problems and suggest steps to fix them. When working on code projects, ONLY AND ONLY IF THE PROJECT IS CLEARLY A CODING ONE please provide the following:\n1. Project Name: Create a concise and appropriate project name that fits the project based on what it's creating. The project name should be no more than 20 characters long.\n2. Folder Structure: Provide the folder structure as a valid JSON object, where each key represents a folder or file, and nested keys represent subfolders. Use null values for files. Ensure the JSON is properly formatted without any syntax errors. Please make sure all keys are enclosed in double quotes, and ensure objects are correctly encapsulated with braces, separating items with commas as necessary.\nWrap the JSON object in <folder_structure> tags.\n3. Code Files: For each code file, include ONLY the file name NEVER EVER USE THE FILE PATH OR ANY OTHER FORMATTING YOU ONLY USE THE FOLLOWING format 'Filename: <filename>' followed by the code block enclosed in triple backticks, with the language identifier after the opening backticks, like this:\n\n​python\n<code>\n​"}]
        }
    ]

    opus_response = client.messages.create(
        model=REFINER_MODEL,
        max_tokens=4096,
        messages=messages
    )

    response_text = opus_response.content[0].text.strip()

    # Check if the response_text is empty or whitespace
    while not response_text:
        console.print(Panel("Empty response received from the refiner. Retrying...", title="[bold yellow]Empty Refiner Response[/bold yellow]", title_align="left", border_style="yellow"))
        opus_response = client.messages.create(
            model=REFINER_MODEL,
            max_tokens=4096,
            messages=messages
        )
        response_text = opus_response.content[0].text.strip()

    console.print(f"Input Tokens: {opus_response.usage.input_tokens}, Output Tokens: {opus_response.usage.output_tokens}")
    total_cost = calculate_subagent_cost(REFINER_MODEL, opus_response.usage.input_tokens, opus_response.usage.output_tokens)
    console.print(f"Refine Cost: ${total_cost:.4f}")

    if opus_response.usage.output_tokens >= 4000 and not continuation:  # Threshold set to 4000 as a precaution
        console.print("[bold yellow]Warning:[/bold yellow] Output may be truncated. Attempting to continue the response.")
        continuation_response_text = opus_refine(objective, sub_task_results + [response_text], filename, projectname, continuation=True)
        response_text += "\n" + continuation_response_text

    # Check if the refiner encountered any issues or if the task is not complete
    if "missing code" in response_text.lower() or "error" in response_text.lower() or "issue" in response_text.lower() or "problem" in response_text.lower() or "unable to resolve" in response_text.lower():
        console.print(Panel("Refiner encountered issues or task is not complete. Sending back to Orchestrator.", title="[bold yellow]Refinement Issues[/bold yellow]", title_align="left", border_style="yellow"))
        orchestrator_prompt = f"The refiner encountered the following issues while refining the sub-task results:\n{response_text}\n\nPlease provide a new set of sub-tasks to address these issues and complete the objective."
        return opus_orchestrator(objective, previous_results=sub_task_results + [orchestrator_prompt], use_search=True)
    else:
        console.print(Panel(response_text, title="[bold green]Final Output[/bold green]", title_align="left", border_style="green"))
        return response_text


def read_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    return content

class CodingAgent:
    def __init__(self, code_interpreter: CodeInterpreter):
        self.code_interpreter = code_interpreter

    def execute_code(self, code_blocks: List[str], existing_codebase_path: str = None) -> Tuple[List[Result], Logs]:
        if existing_codebase_path:
            # Read code files from the existing codebase
            code_files = self._read_code_files(existing_codebase_path)
            # Prepend the existing code to the generated code
            code_blocks = code_files + code_blocks

        results = []
        logs = Logs(stdout=[], stderr=[])

        for code_block in code_blocks:
            print(f"\n{'='*50}\n> Running following AI-generated code:\n{code_block}\n{'='*50}")
            if '```python' in code_block:
                execution = self.code_interpreter.notebook.exec_cell(code_block)
            elif '```javascript' in code_block or '```typescript' in code_block:
                execution = self.code_interpreter.notebook.exec_cell(code_block, kernel_id='Node16')
            else:
                continue  # Skip execution if the language is not supported

            if execution.error:
                print("[Code Interpreter error]", execution.error)
                error_message = f"Error executing the generated code:\n{execution.error.name}: {execution.error.value}\n{execution.error.traceback_raw}"
                logs.stderr.append(error_message)
            else:
                results.extend(execution.results)
                logs.stdout.extend(execution.logs.stdout)
                logs.stderr.extend(execution.logs.stderr)

        return results, logs

    def _read_code_files(self, codebase_path: str) -> List[str]:
        code_files = []
        for root, _, files in os.walk(codebase_path):
            for file in files:
                if file.endswith(".py") or file.endswith(".js") or file.endswith(".ts"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r") as f:
                        code_files.append(f.read())
        return code_files

def create_folder_structure(project_name, folder_structure, code_blocks):
    # Create the project folder
    try:
        os.makedirs(project_name, exist_ok=True)
        console.print(Panel(f"Created project folder: [bold]{project_name}[/bold]", title="[bold green]Project Folder[/bold green]", title_align="left", border_style="green"))
    except OSError as e:
        console.print(Panel(f"Error creating project folder: [bold]{project_name}[/bold]\nError: {e}", title="[bold red]Project Folder Creation Error[/bold red]", title_align="left", border_style="red"))
        return

    # Recursively create the folder structure and files
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

def maestro_dev(objective, existing_codebase_path=None):
    # Get the objective from user input
    objective = input("Please enter your objective with or without a text file path: ")

    # Check if the input contains a file path
    if "./" in objective or "/" in objective:
        # Extract the file path from the objective
        file_path_match = re.findall(r'[./\w]+\.[\w]+', objective)
        if file_path_match:
            file_path = file_path_match[0]
            # Read the file content
            with open(file_path, 'r') as file:
                file_content = file.read()
            # Update the objective string to remove the file path
            objective = objective.split(file_path)[0].strip()
        else:
            file_content = None
    else:
        file_content = None

    # Ask the user if they want to use search
    use_search = input("Do you want to use search? (y/n): ").lower() == 'y'

    task_exchanges = []
    haiku_tasks = []

    with CodeInterpreter() as code_interpreter:
        coding_agent = CodingAgent(code_interpreter)

        while True:
            # Call Orchestrator to break down the objective into the next sub-task or provide the final output
            previous_results = [result for _, result in task_exchanges]
            if not task_exchanges:
                # Pass the file content only in the first iteration if available
                opus_result, file_content_for_haiku, search_query = opus_orchestrator(objective, file_content, previous_results, use_search, task_exchanges)
            else:
                #opus_result, _, search_query = opus_orchestrator(objective, previous_results=previous_results, use_search=use_search)
                opus_result, _, search_query = opus_orchestrator(objective, previous_results=previous_results, use_search=use_search, task_exchanges=task_exchanges)

            if "The task is complete:" in opus_result:
                # If Opus indicates the task is complete, check if the code execution was successful
                if not any("Error executing the generated code" in result for _, result in task_exchanges):
                    final_output = opus_result.replace("The task is complete:", "").strip()
                    console.print(Panel(final_output, title="[bold green]Task Complete[/bold green]", title_align="left", border_style="green"))
                    break
                else:
                    # If there were code execution errors, continue the loop for further refinements
                    console.print(Panel("Code execution errors detected. Continuing refinement process.", title="[bold yellow]Refinement Needed[/bold yellow]", title_align="left", border_style="yellow"))
                    continue
            else:
                sub_task_prompt = opus_result
                # Append file content to the prompt for the initial call to haiku_sub_agent, if applicable
                if file_content_for_haiku and not haiku_tasks:
                    sub_task_prompt = f"{sub_task_prompt}\n\nFile content:\n{file_content_for_haiku}"
                # Check if the sub-task involves coding
                if "code" in sub_task_prompt.lower() or "coding" in sub_task_prompt.lower() or "programming" in sub_task_prompt.lower():
                    # Call haiku_sub_agent to generate code
                    code_response = haiku_sub_agent(sub_task_prompt, search_query, haiku_tasks, use_search)
                
                    # Extract code blocks from the response
                    code_blocks = re.findall(r'```(?:python|javascript|html|css)?\n(.*?)\n```', code_response, re.DOTALL)
                
                    if code_blocks:
                        # Execute the code blocks using the CodingAgent
                        code_results, code_logs = coding_agent.execute_code(code_blocks, existing_codebase_path)
                    
                        if code_logs.stderr:
                            # If there are errors in the code execution, provide feedback to the user or AI agent
                            error_feedback = f"The generated code encountered the following error(s):\n{' '.join(code_logs.stderr)}\n\nPlease review and fix the code before proceeding."
                            console.print(Panel(error_feedback, title="[bold red]Code Execution Error[/bold red]", title_align="left", border_style="red"))
                            # Pass the error feedback to the orchestrator as part of the previous results
                            task_exchanges.append((sub_task_prompt, error_feedback))
                        else:
                            # If the code execution is successful, pass the code results to the orchestrator
                            task_exchanges.append((sub_task_prompt, code_results))
                            haiku_tasks.append({"task": sub_task_prompt, "result": code_results})
                    else:
                        console.print(Panel("No code blocks found in the response.", title="[bold yellow]Code Blocks Not Found[/bold yellow]", title_align="left", border_style="yellow"))
                        task_exchanges.append((sub_task_prompt, code_response))
                else:
                    # Call haiku_sub_agent with the prepared prompt, search query, and record the result
                    sub_task_result = haiku_sub_agent(sub_task_prompt, search_query, haiku_tasks, use_search)
                    # Log the task and its result for future reference
                    haiku_tasks.append({"task": sub_task_prompt, "result": sub_task_result})
                    # Record the exchange for processing and output generation
                    task_exchanges.append((sub_task_prompt, sub_task_result))
                # Prevent file content from being included in future haiku_sub_agent calls
                file_content_for_haiku = None
        # Create the .md filename
        sanitized_objective = re.sub(r'\W+', '_', objective)
        timestamp = datetime.now().strftime("%H-%M-%S")

        # Call Opus to review and refine the sub-task results
        refined_output = opus_refine(objective, [result for _, result in task_exchanges], timestamp, sanitized_objective)

        # Extract the project name from the refined output
        project_name_match = re.search(r'Project Name: (.*)', refined_output)
        project_name = project_name_match.group(1).strip() if project_name_match else sanitized_objective

        # Extract the folder structure from the refined output
        folder_structure_match = re.search(r'<folder_structure>(.*?)</folder_structure>', refined_output, re.DOTALL)
        folder_structure = {}
        if folder_structure_match:
            json_string = folder_structure_match.group(1).strip()
            try:
                folder_structure = json.loads(json_string)
            except json.JSONDecodeError as e:
                console.print(Panel(f"Error parsing JSON: {e}", title="[bold red]JSON Parsing Error[/bold red]", title_align="left", border_style="red"))
                console.print(Panel(f"Invalid JSON string: [bold]{json_string}[/bold]", title="[bold red]Invalid JSON String[/bold red]", title_align="left", border_style="red"))

        # Extract code files from the refined output
        code_blocks = re.findall(r'Filename: (\S+)\s*```[\w]*\n(.*?)\n```', refined_output, re.DOTALL)

        # Create the folder structure and code files
        create_folder_structure(project_name, folder_structure, code_blocks)

        # Truncate the sanitized_objective to a maximum of 50 characters
        max_length = 25
        truncated_objective = sanitized_objective[:max_length] if len(sanitized_objective) > max_length else sanitized_objective

        # Update the filename to include the project name
        filename = f"{timestamp}_{truncated_objective}.md"

        # Prepare the full exchange log
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


if __name__ == "__main__":
    existing_codebase_path = None  # Set the path to the existing codebase if applicable
    maestro_dev(objective="", existing_codebase_path=existing_codebase_path)