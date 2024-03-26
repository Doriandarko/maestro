import os
from anthropic import Anthropic
import re
from rich.console import Console
from rich.panel import Panel
from datetime import datetime

# Set up the Anthropic API client
client = Anthropic(api_key="")

# Initialize the Rich Console
console = Console()

def opus_orchestrator(objective, previous_results=None):
    console.print(f"\n[bold]Calling Opus for your objective[/bold]")
    previous_results_text = "\n".join(previous_results) if previous_results else "None"
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"Based on the following objective and the previous sub-task results (if any), please break down the objective into the next sub-task, and create a concise and detailed prompt for a subagent so it can execute that task, please assess if the objective has been fully achieved. If the previous sub-task results comprehensively address all aspects of the objective, include the phrase 'The task is complete:' at the beginning of your response. If the objective is not yet fully achieved, break it down into the next sub-task and create a concise and detailed prompt for a subagent to execute that task.:\n\nObjective: {objective}\n\nPrevious sub-task results:\n{previous_results_text}"}
            ]
        }
    ]

    opus_response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=4096,
        messages=messages
    )

    response_text = opus_response.content[0].text
    console.print(Panel(response_text, title=f"[bold green]Opus Orchestrator[/bold green]", title_align="left", border_style="green", subtitle="Sending task to Haiku 👇"))
    return response_text

def haiku_sub_agent(prompt, previous_haiku_tasks=None):
    if previous_haiku_tasks is None:
        previous_haiku_tasks = []

    system_message = "Previous Haiku tasks:\n" + "\n".join(previous_haiku_tasks)

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt}
            ]
        }
    ]

    haiku_response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=4096,
        messages=messages,
        system=system_message
    )

    response_text = haiku_response.content[0].text
    console.print(Panel(response_text, title="[bold blue]Haiku Sub-agent Result[/bold blue]", title_align="left", border_style="blue", subtitle="Task completed, sending result to Opus 👇"))
    return response_text

def opus_refine(objective, sub_task_results, filename):
    print(f"\nCalling Opus to provide the refined final output for your objective:")
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"Objective: {objective}\n\nSub-task results:\n" + "\n".join(sub_task_results) + "\n\nPlease review and refine the sub-task results into a cohesive final output. Add any missing information or details as needed. When working on code projects make sure to include the code implementation by file. When displaying the file name it is VERY important you always format it this way 'Filename: index.html' for instance, of course, the file name can be different."}
            ]
        }
    ]

    opus_response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=4096,
        messages=messages
    )

    response_text = opus_response.content[0].text
    console.print(Panel(response_text, title="[bold green]Final Output[/bold green]", title_align="left", border_style="green"))

    # Extract code files from the final output
    code_blocks = re.findall(r'Filename: (\S+)\s*```[\w]*\n(.*?)\n```', response_text, re.DOTALL)

    # Create code files using function calling
    for file_name, code_content in code_blocks:
        console.print(Panel(f"Creating file: [bold]{file_name}[/bold]", title="[bold blue]File Creation[/bold blue]", title_align="left", border_style="blue"))

        # Save the code file in the corresponding folder
        folder_name = os.path.splitext(filename)[0]
        os.makedirs(folder_name, exist_ok=True)
        file_path = os.path.join(folder_name, file_name)
        with open(file_path, 'w') as file:
            file.write(code_content)

    return response_text

def read_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    return content

# Get the objective from user input
objective = input("Please enter your objective with or without a text file path: ")

# Check if the input contains a file path
if "./" in objective or "/" in objective:
    # Extract the file path from the objective
    file_path = re.findall(r'[./\w]+\.[\w]+', objective)[0]
    # Read the file content
    with open(file_path, 'r') as file:
        file_content = file.read()
    # Update the objective string to include the instruction and file content
    objective = f"{objective}\n\nFile content:\n{file_content}"
else:
    objective = objective
    

task_exchanges = []
haiku_tasks = []

while True:
    # Call Opus to break down the objective into the next sub-task or provide the final output
    previous_results = [result for _, result in task_exchanges]
    opus_result = opus_orchestrator(objective, previous_results)

    if "The task is complete:" in opus_result:
        # If Opus indicates the task is complete, exit the loop
        final_output = opus_result.replace("The task is complete:", "").strip()
        break
    else:
        sub_task_prompt = opus_result
        sub_task_result = haiku_sub_agent(sub_task_prompt, haiku_tasks)
        haiku_tasks.append(f"Task: {sub_task_prompt}\nResult: {sub_task_result}")
        task_exchanges.append((sub_task_prompt, sub_task_result))

# Create the filename
sanitized_objective = re.sub(r'\W+', '_', objective)
timestamp = datetime.now().strftime("%H-%M-%S")
filename = f"{timestamp}_{sanitized_objective[:50]}.md" if len(sanitized_objective) > 50 else f"{timestamp}_{sanitized_objective}.md"

# Call Opus to review and refine the sub-task results
refined_output = opus_refine(objective, [result for _, result in task_exchanges], filename)

# ...

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

sanitized_objective = re.sub(r'\W+', '_', objective)
# Create a unique identifier of objective
timestamp = datetime.now().strftime("%H-%M-%S")
# Guard against filename too long OS errors by conditionally combining unique hash as prefix
filename = f"{timestamp}_{sanitized_objective[:50]}.md" if len(sanitized_objective) > 50 else f"{timestamp}_{sanitized_objective}.md"

with open(filename, 'w') as file:
    file.write(exchange_log)
print(f"\nFull exchange log saved to {filename}")
