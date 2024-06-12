import mistletoe
import os
import black

def read_markdown_file(file_path):
    """
    Reads the content of a markdown file.

    Args:
        file_path (str): The path to the markdown file.

    Returns:
        str: The content of the markdown file.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")

def format_markdown(markdown_content):
    """
    Formats markdown content according to a chosen style guide.

    Args:
        markdown_content (str): The raw markdown content.

    Returns:
        str: The formatted markdown content.
    """
    tree = mistletoe.Document(markdown_content)
    formatted_content = ""

    def format_element(element, level=0):
        """
        Recursively formats elements within the markdown tree.
        """
        nonlocal formatted_content
        indent = "  " * level

        if isinstance(element, mistletoe.Heading):
            formatted_content += f"{indent}#{element.level} {element.content}\n"
        elif isinstance(element, mistletoe.List):
            for item in element.children:
                formatted_content += f"{indent}- {item.content}\n"
        elif isinstance(element, mistletoe.Paragraph):
            formatted_content += f"{indent}{element.content}\n"
        elif isinstance(element, mistletoe.CodeBlock):
            formatted_content += f"{indent}{element.content}\n"
        elif isinstance(element, mistletoe.Link):
            formatted_content += f"{indent}[{element.content}]({element.target})\n"
        elif isinstance(element, mistletoe.Image):
            formatted_content += f"{indent}![{element.alt}]({element.src})\n"
        elif isinstance(element, mistletoe.HTMLBlock):
            formatted_content += f"{indent}{element.content}\n"
        else:
            for child in element.children:
                format_element(child, level + 1)

    format_element(tree)
    return formatted_content

def format_markdown_files(directory):
    """
    Formats all markdown files in a given directory.
    """
    for filename in os.listdir(directory):
        if filename.endswith(".md"):
            filepath = os.path.join(directory, filename)
            try:
                markdown_content = read_markdown_file(filepath)
                formatted_content = format_markdown(markdown_content)
                black.format_file_contents(filepath, content=formatted_content)
                print(f"Formatted: {filename}")
            except FileNotFoundError as e:
                print(f"Error: {e}")
            except mistletoe.core.MistletoeError as e:
                print(f"Invalid Markdown in {filename}: {e}")

if __name__ == "__main__":
    # Example usage
    format_markdown_files("my_markdown_files")