import os
import datetime
from dotenv import load_dotenv

load_dotenv()

anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
tavily_api_key = os.getenv('TAVILY_API_KEY')
openai_api_key = os.getenv('OPENAI_API_KEY')
groq_api_key = os.getenv('GROQ_API_KEY')

objectives_dir = os.path.join(os.path.dirname(
    __file__), 'objectives', datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
