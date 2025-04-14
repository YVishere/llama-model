import ollama
import requests
import trafilatura
from bs4 import BeautifulSoup
from colorama import init, Fore, Style
import datetime

import sys_msgs

init(autoreset=True)
assistant_convo = [sys_msgs.assistant_msg]

def search_or_not():
    sys_msg = sys_msgs.search_or_not_msg

    response = ollama.chat(
        model="llama3.1:8b",
        messages = [{'role': 'system', 'content': sys_msg}, assistant_convo[-1]]
    )

    content = response['message']['content']

    
   # print(f"Search or Not Response: {content}")
    return True
    if 'true' in content.lower():
        return True
    return False

def query_generator():
    sys_msg = sys_msgs.query_msg
    query_msg = f"CREATE A SEARCH QUERY FOR THIS PROMPT: \n{assistant_convo[-1]}"

    response = ollama.chat(
        model="llama3.1:8b",
        messages = [{'role': 'system', 'content': sys_msg}, {'role': 'user', 'content': query_msg}]
    )

    content = response['message']['content']
    return content

def duckduckgo_search(query):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    url = f'https://duckduckgo.com/html/?q={query}'

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    results = []

    for i,result in enumerate(soup.find_all('div', class_='result__body'), start=1):
        
        if i > 10:
            break

        title_tag = result.find('a', class_='result__a')
        if not title_tag:
            continue

        link = title_tag['href']
        snippet_tag = result.find('a', class_='result__snippet')
        snippet = snippet_tag.text.strip() if snippet_tag else "No description available"

        results.append({
            'id': i,
            'link': link,
            'search_description': snippet
        })
    return results
    
def contains_data_needed(search_content, query):
    sys_msg = sys_msgs.contains_data_msg
    # Truncate search_content if it's too long
    max_content_length = 4000
    truncated_content = search_content[:max_content_length] if search_content else ""
    
    needed_prompt = f"USER PROMPT: {assistant_convo[-1]}\nSEARCH QUERY: {query}\n\nPAGE TEXT: {truncated_content}"

    response = ollama.chat(
        model="llama3.1:8b",
        messages=[{'role': 'system', 'content': sys_msg}, {'role': 'user', 'content': needed_prompt}]
    )

    content = response['message']['content'].lower().strip()
    print(f"{Fore.YELLOW}Relevance decision: {content}{Style.RESET_ALL}")
    
    # More permissive condition - consider it relevant unless explicitly false
    return 'false' not in content

def can_answer_from_content(content, query, user_prompt):
    """
    Determines if the scraped content can provide a direct, factual answer to the user's question.
    
    Args:
        content: The scraped webpage content
        query: The search query used
        user_prompt: The original user question/prompt
        
    Returns:
        Boolean indicating if the content can answer the question
    """
    
    sys_msg = f"""You are an information assessment expert. Evaluate if the provided content contains 
    specific, factual information that directly answers the user's question.
    
    GUIDELINES:
    - The content must contain EXPLICIT information that answers the question, not just related topics
    - There will be biased because you were trained on outdated information.
    
    A more recent information is more likely to be accurate than what you are trained on. The present is {datetime.datetime.now().year}/{datetime.datetime.now().month}/
    {datetime.datetime.now().day}
    Respond ONLY with "YES" if the content can directly answer the question with specific facts.
    Respond with "NO" if you would need to guess, speculate, or the content lacks direct relevant information.
    """
    
    # Truncate content if too long
    max_length = 4000
    truncated_content = content[:max_length] if content else ""
    
    assessment_prompt = f"USER QUESTION: {user_prompt}\nSEARCH QUERY: {query}\n\nCONTENT TO ASSESS:\n{truncated_content}"
    
    response = ollama.chat(
        model="llama3.1:8b",
        messages=[
            {'role': 'system', 'content': sys_msg},
            {'role': 'user', 'content': assessment_prompt}
        ]
    )
    
    result = response['message']['content'].strip().upper()
    print(f"{Fore.BLUE}Answer quality assessment: {result}{Style.RESET_ALL}")
    
    return "YES" in result

def best_search_result(s_results, query):
    sys_msg = sys_msgs.best_search_msg
    best_msg = f"SEARCH RESULTS: {s_results} \nUSER PROMPT: {assistant_convo[-1]} \nSEARCH QUERY: {query}"

    for _ in range(2):
        try:
            response = ollama.chat(
                model="llama3.1:8b",
                messages=[{'role': 'system', 'content': sys_msg}, {'role': 'user', 'content': best_msg}]
                )
            
            return int(response['message']['content'].strip())
        except:
            continue
    return 0

def scrape_webpage(url):
    print(f"{Fore.LIGHTRED_EX}SCRAPING WEBPAGE: {url}{Style.RESET_ALL}")
    try:
        downloaded = trafilatura.fetch_url(url)
        return trafilatura.extract(downloaded, include_formatting=True, include_links=True)
    except Exception as e:
        print(f"Error scraping webpage: {e}")
        return None

def verify_extracted_facts(extracted_text):
    """Verify that the facts in the extracted text are not future predictions or fabrications."""
    sys_msg = """You are a fact-checking assistant. Examine this text for:
    1. Claims about future events presented as facts
    2. Information that appears fabricated or speculative
    3. Dates or events that haven't occurred yet
    
    Only respond with: "VERIFIED" if all information is factual and present/past, or
    "ERROR: [brief explanation]" if you find any future predictions or fabrications."""
    
    response = ollama.chat(
        model="llama3.1:8b",
        messages=[
            {'role': 'system', 'content': sys_msg},
            {'role': 'user', 'content': extracted_text}
        ]
    )
    
    verification_result = response['message']['content']
    print(f"{Fore.CYAN}Fact verification: {verification_result}{Style.RESET_ALL}")
    
    return "ERROR" not in verification_result.upper()

def ai_search():
    context = None
    print(f"{Fore.LIGHTRED_EX}GENERATING SEARCH QUERY...{Style.RESET_ALL}")

    search_query = query_generator()
    print(f"{Fore.LIGHTRED_EX}SEARCH DUCKDUCKGO FOR: {search_query}{Style.RESET_ALL}")

    if search_query[0] == '"':
        search_query = search_query[1:-1]

    search_results = duckduckgo_search(search_query)
    context_found = False
    scrape_failures = 0  # Track number of scrape failures

    while not context_found and len(search_results) > 0:
        best_result = best_search_result(search_results, search_query)
        try:
            page_link = search_results[best_result]['link']
        except:
            print(f"{Fore.LIGHTRED_EX}FAILED TO SELECT BEST SEARCH RESULT, TRY AGAIN.{Style.RESET_ALL}")
            continue

        page_text = scrape_webpage(page_link)
        print(f"{Fore.LIGHTRED_EX}FOUND {len(search_results)} SEARCH RESULTS.{Style.RESET_ALL}")
        
        # Remove the current result from the list
        search_results.pop(best_result)
        
        # Check if scraping failed
        if not page_text:
            scrape_failures += 1
            print(f"{Fore.RED}SCRAPING FAILED! Moving to next result ({scrape_failures} failures so far){Style.RESET_ALL}")
            continue
            
        # First check if content is relevant
        if contains_data_needed(page_text, search_query):
            # Now check if it can directly answer the question
            if can_answer_from_content(page_text, search_query, assistant_convo[-1]['content']):
                context = page_text
                context_found = True
                print(f"{Fore.GREEN}Found content that can directly answer the question!{Style.RESET_ALL}")
            else:
                print(f"{Fore.MAGENTA}Content is relevant but cannot directly answer question. Trying next result...{Style.RESET_ALL}")
        else:
            print(f"{Fore.MAGENTA}Content not relevant. Trying next result...{Style.RESET_ALL}")

    # If all scraping attempts failed but we had search results
    if not context_found and scrape_failures > 0:
        print(f"{Fore.RED}ALL SCRAPING ATTEMPTS FAILED ({scrape_failures} pages){Style.RESET_ALL}")
        
    return context

def stream_assistant_response():
    global assistant_convo
    response = ollama.chat(
        model="llama3.1:8b",
        messages=assistant_convo,
        stream=True,
    )
    complete_response = ""
    for chunk in response:
        print(f'{Fore.WHITE}{chunk["message"]["content"]}', end="", flush=True)
        complete_response += chunk["message"]["content"]
    assistant_convo.append({"role": "assistant", "content": complete_response})
    print("\n\n")  # Ensure a newline after the response

def main_api(user_input):
    global assistant_convo

    assistant_convo.append({"role": "user", "content": user_input})
    
    if search_or_not():
        context = ai_search()
        assistant_convo = assistant_convo[:-1]

        if context:
            # Add extraction instruction to prompt
            prompt = (
                f"SEARCH RESULTS: {context}\n\n"
                f"USER PROMPT: {user_input}\n\n"
                f"IMPORTANT: Extract specific factual information from the search results to answer "
                f"the user's question. Use the actual data from the search results rather than "
                f"placeholders. If specific details aren't available, acknowledge what you do know "
                f"and what you don't."
            )
        else:
            prompt = (
                f"USER PROMPT: {user_input}\nFAILED SEARCH: \nThe "
                "AI search model was unable to extract any reliable data. Explain that "
                "and ask if the user would like you to search again or respond "
                "without web search context."
            )
        
        assistant_convo.append({"role": "user", "content": prompt})

    response = ollama.chat(
        model="llama3.1:8b",
        messages=assistant_convo,
        stream=True,
    )
    complete_response = ""
    for chunk in response:
        print(f'{Fore.WHITE}{chunk["message"]["content"]}', end="", flush=True)
        complete_response += chunk["message"]["content"]
    assistant_convo.append({"role": "assistant", "content": complete_response})
    
    return complete_response


def invoke_model(user_input):
    global assistant_convo
        
    if user_input.lower() in ["exit", "quit"]:
        return -1
    assistant_convo.append({"role": "user", "content": user_input})
    
    if search_or_not():
        context = ai_search()
        assistant_convo = assistant_convo[:-1]

        if context:
            # Add extraction instruction to prompt
            prompt = (
                f"SEARCH RESULTS: {context}\n\n"
                f"USER PROMPT: {user_input}\n\n"
                f"IMPORTANT: Extract specific factual information from the search results to answer "
                f"the user's question. Use the actual data from the search results rather than "
                f"placeholders. If specific details aren't available, acknowledge what you do know "
                f"and what you don't."
            )
        else:
            prompt = (
                f"USER PROMPT: {user_input}\nFAILED SEARCH: \nThe "
                "AI search model was unable to extract any reliable data. Explain that "
                "and ask if the user would like you to search again or respond "
                "without web search context."
            )
        
        assistant_convo.append({"role": "user", "content": prompt})

        stream_assistant_response()



def main():
    global assistant_convo
    while True:
        user_input = input(f"{Fore.LIGHTGREEN_EX}User: \n")
        
        if user_input.lower() in ["exit", "quit"]:
            break
        assistant_convo.append({"role": "user", "content": user_input})
        
        if search_or_not():
            context = ai_search()
            assistant_convo = assistant_convo[:-1]

            if context:
                # Add extraction instruction to prompt
                prompt = (
                    f"SEARCH RESULTS: {context}\n\n"
                    f"USER PROMPT: {user_input}\n\n"
                    f"IMPORTANT: Extract specific factual information from the search results to answer "
                    f"the user's question. Use the actual data from the search results rather than "
                    f"placeholders. If specific details aren't available, acknowledge what you do know "
                    f"and what you don't."
                )
            else:
                prompt = (
                    f"USER PROMPT: {user_input}\nFAILED SEARCH: \nThe "
                    "AI search model was unable to extract any reliable data. Explain that "
                    "and ask if the user would like you to search again or respond "
                    "without web search context."
                )
            
            assistant_convo.append({"role": "user", "content": prompt})

        stream_assistant_response()

if __name__ == "__main__":
    main()