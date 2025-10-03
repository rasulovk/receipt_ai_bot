from ollama import Client
from dataclasses import dataclass
# from mem0 import Memory

@dataclass
class OllamaState:
    """
    Arguments
    ==========
    ollama_client: The Ollama client to use for sending messages.
    model: The model to use for inference.
    message_chunk_size: The number of words to be sent at a time.
    """
    client: Client
    model: str
    message_chunk_size: int
    # memory: Memory = None  # Add memory as an optional field

ollama_state: OllamaState = None



def init_ollama_state(client: Client, model: str, chunk_size: int):
    global ollama_state
    # global memory
    # # Configure mem0 to use Ollama as the LLM provider
    # MEM0_CONFIG = {
    #     "llm": {
    #         "provider": "ollama",
    #         "config": {
    #             "model": model,  # or your preferred model
    #             "temperature": 0.1,
    #             "max_tokens": 4000,
    #         }
    #     },
    #     "embedder": {
    #         "provider": "ollama",
    #         "config": {
    #             "model": "mxbai-embed-large",
    #             "embedding_dims": 1024,
    #             # "embedding_dims": 1024, # Adjust based on your model
    #         }
    #     },
    #     "vector_store": {
    #         "provider": "qdrant",
    #         "config": {
    #             "collection_name": "test",
    #             "path": "./qdrant_data",
    #             "host": "localhost",
    #             # "url": "https://qdrant.dadiba.win",
    #             "port": 443,
    #             "embedding_model_dims": 1024,
    #         }
    #     }
    # }
    # # Initialize mem0 Memory with Ollama config
    # memory = Memory.from_config(MEM0_CONFIG)
    # memory.add("I'm visiting Paris", user_id="TELEGRAM_USER_ID")
    # ollama_state = OllamaState(client=client, model=model, message_chunk_size=chunk_size, memory=memory)
    ollama_state = OllamaState(client=client, model=model, message_chunk_size=chunk_size)


# def ollama_chat_mem(prompt: str, chat_id: str, model: str = None):
#     """
#     Chat with Ollama and store/retrieve all user memories.
#     """
#     if model is None:
#         model = ollama_state.model
#     memories = memory.get_all(user_id=chat_id)
#     print(f"[OLLAMA CLient - Chat] Stored is : {memories} . ID is: {chat_id}" )
#     # Retrieve all previous memories for this user
#     previous_memories = memory.get_all(user_id=str(chat_id))
#     # memories_str = "\n".join(f"- {entry['memory']}" for entry in previous_memories)
#     memories_str = "\n".join(f"- {entry}" for entry in previous_memories)

#     # Build system prompt with all memories
#     if memories_str:
#         system_prompt = f"User memories:\n{memories_str}\n\n"
#     else:
#         system_prompt = ""
#     full_prompt = f"{system_prompt}{prompt}"

#     # Compose messages for LLM
#     messages = [{"role": "user", "content": full_prompt}]

#     # Use Ollama client directly
#     response = ollama_state.client.chat(
#         model=model,
#         messages=messages,
#     )

#     # Extract assistant response
#     if hasattr(response, "message") and hasattr(response.message, "content"):
#         assistant_response = response.message.content
#     elif isinstance(response, dict) and "message" in response and "content" in response["message"]:
#         assistant_response = response["message"]["content"]
#     elif isinstance(response, str):
#         assistant_response = response
#     else:
#         raise ValueError(f"Unexpected response from ollama client: {response}")

#     messages.append({"role": "assistant", "content": assistant_response})
#     memory.add(messages, user_id=str(chat_id))
#     return assistant_response


def ollama_chat(prompt: str, model: str = None):
    if model is None:
        model = ollama_state.model
    print(f"[OLLAMA CLient - Chat] Using model: {model}")
    return ollama_state.client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )["message"]["content"]

def ollama_vision(prompt: str, image_path: str, model: str = "llama3.2-vision:latest"):
    print(f"[OLLAMA CLient - Vision] Using model: {model}")
    return ollama_state.client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt, "images": [image_path]}],
    )
    # print(f"[DEBUG] ollama_vision result: {result}")
    # if isinstance(result, dict) and "message" in result and "content" in result["message"]:
    #     return result["message"]["content"]
    # elif isinstance(result, str):
    #     return result
    # else:
    #     raise ValueError(f"Unexpected response from ollama client: {result}")

# Example usage from ollama web site
# import ollama

# response = ollama.chat(
#     model='llama3.2-vision',
#     messages=[{
#         'role': 'user',
#         'content': 'What is in this image?',
#         'images': ['image.jpg']
#     }]
# )

# print(response)



def get_current_model():
    return ollama_state.model if ollama_state else "unknown"