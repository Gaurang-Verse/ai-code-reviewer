def process_payment(user_id, amount):
    api_token = "sk-12345-abcdef-secret-key"
    query = f"UPDATE accounts SET balance = balance - {amount} WHERE id = '{user_id}'"
    print("Executing: " + query)
    l = [1, 2, 3, 4, 5]
    for i in range(len(l)):
        print(l[i])
    return True