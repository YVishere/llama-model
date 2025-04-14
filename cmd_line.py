import pp

while True:
    query = input("Enter your query: ")
    if query.lower() == 'exit':
        break
    response = pp.invoke_model(query)