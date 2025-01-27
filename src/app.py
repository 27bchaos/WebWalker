import streamlit as st
import os
import json5
from agent import WebWalker
from qwen_agent.tools.base import BaseTool, register_tool
import re
import json
import asyncio
from utils import *
import base64
from PIL import Image
from bs4 import BeautifulSoup

# Manually set the API key
os.environ['OPENAI_API_KEY'] = 'your_openai_api_key'

# Validate required environment variables
if 'DASHSCOPE_API_KEY' not in os.environ and ('OPENAI_API_KEY' not in os.environ or 'OPENAI_MODEL_SERVER' not in os.environ):
    raise ValueError("Please set 'DASHSCOPE_API_KEY' or both 'OPENAI_API_KEY' and 'OPENAI_MODEL_SERVER'.")

# Initialize llm_cfg
llm_cfg = None

if 'DASHSCOPE_API_KEY' in os.environ:
    model = "qwen-plus"
    llm_cfg = {
        'model': model,
        'api_key': os.getenv('DASHSCOPE_API_KEY'),
        'model_server': "https://dashscope.aliyuncs.com/compatible-mode/v1",
        'generate_cfg': {
            'top_p': 0.8,
            'max_input_tokens': 120000,
            'max_retries': 20,
        },
    }
elif 'OPENAI_API_KEY' in os.environ and 'OPENAI_MODEL_SERVER' in os.environ:
    model = "gpt-4o"
    llm_cfg = {
        'model': model,
        'api_key': os.getenv('OPENAI_API_KEY'),
        'model_server': os.getenv('OPENAI_MODEL_SERVER'),
        'generate_cfg': {
            'top_p': 0.8,
            'max_input_tokens': 120000,
            'max_retries': 20,
        },
    }

def extract_links_with_text(html):
    """
    Extract clickable links and buttons from the provided HTML content.
    
    Args:
        html (str): The HTML content of the webpage.
    
    Returns:
        str: A string containing clickable buttons.
    """
    with open("ROOT_URL.txt", "r") as f:
        ROOT_URL = f.read()
    soup = BeautifulSoup(html, 'html.parser')
    links = []

    for a_tag in soup.find_all('a', href=True):
        url = a_tag['href']
        text = ''.join(a_tag.stripped_strings)
        if text and "javascript" not in url and not url.endswith(('.jpg', '.png', '.gif', '.jpeg', '.pdf')):
            if process_url(ROOT_URL, url).startswith(ROOT_URL):
                links.append({'url': process_url(ROOT_URL, url), 'text': text})

    for button in soup.find_all('button', onclick=True):
        onclick_text = button['onclick']
        text = button.get('title') or button.get('aria-label') or ''.join(button.stripped_strings)
        match = re.search(r"window\.location\.href='([^']*)'", onclick_text)
        if match:
            url = match.group(1)
            if url and text:
                if process_url(ROOT_URL, url).startswith(ROOT_URL):
                    links.append({'url': process_url(ROOT_URL, url), 'text': text})

    unique_links = {f"{item['url']}_{item['text']}": item for item in links}

    if not os.path.exists("BUTTON_URL_ADIC.json"):
        with open("BUTTON_URL_ADIC.json", "w") as f:
            json.dump({}, f)
    with open("BUTTON_URL_ADIC.json", "r") as f:
        BUTTON_URL_ADIC = json.load(f)
    for temp in list(unique_links.values()):
        BUTTON_URL_ADIC[temp["text"]] = temp["url"]
    with open("BUTTON_URL_ADIC.json", "w") as f:
        json.dump(BUTTON_URL_ADIC, f)
    info = ""
    for i in list(unique_links.values()):
        info += f"<button>{i['text']}<button>\n"
    return info

if __name__ == "__main__":
    st.title('🤝WebWalker')
    st.markdown("### 📚Introduction")
    st.markdown("👋Welcome to WebWalker! WebWalker is a web-based conversational agent that can help you navigate websites and find information.")
    st.markdown("### 🚀Let's start exploring the website!")

    if 'form_1_text' not in st.session_state:
        st.session_state.form_1_text = ""
    if 'form_2_text' not in st.session_state:
        st.session_state.form_2_text = ""

    with st.sidebar:
        MAX_ROUNDS = st.number_input('Max Action Count:', min_value=1, max_value=15, value=10, step=1)
        website_example = st.sidebar.selectbox('Example Website:', ['https://2025.aclweb.org/'])
        question_example = st.sidebar.selectbox('Example Query:', ["When is the paper submission deadline?", "What is the special theme of ACL 2025?"])

    col1, col2 = st.columns([3, 1])
    with col1:
        with st.form(key='my_form'):
            website = st.text_area('👉Website', value=website_example, placeholder='Input the website you want to walk through.')
            query = st.text_area('🤔Query', value=question_example, placeholder='Input the query you want to ask.')
            submit_button = st.form_submit_button('Start!!!!')

            if submit_button:
                if website and query:
                    tools = ["visit_page"]
                    if llm_cfg is None:
                        st.error("Configuration error: llm_cfg is not defined.")
                    else:
                        llm_cfg["query"] = query
                        llm_cfg["action_count"] = MAX_ROUNDS
                        bot = WebWalker(llm=llm_cfg, function_list=tools)
                        ROOT_URL = website
                        with open("ROOT_URL.txt", "w") as f:
                            f.write(ROOT_URL)
                        html, markdown, screenshot = asyncio.run(get_info(website))
                        st.markdown('**🌐 Now Visiting**')
                        st.write(website)
                        buttons = extract_links_with_text(html)
                        response = f"Website information:\n\n{markdown}\n\nClickable buttons:\n\n{buttons}"
                        st.text(response)
                else:
                    st.error('Please input both the website and query.')
