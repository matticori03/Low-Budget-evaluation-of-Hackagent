from langchain_ollama import ChatOllama
llm = ChatOllama(model="llama3.1:8b", temperature=0, max_tokens=5)
response = llm.invoke("Write a very long story about a dragon.")
print(f"Response with max_tokens: {response.content}")

llm2 = ChatOllama(model="llama3.1:8b", temperature=0, num_predict=5)
response2 = llm2.invoke("Write a very long story about a dragon.")
print(f"Response with num_predict: {response2.content}")
