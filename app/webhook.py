import os
from fastapi import FastAPI, Request, Response
from app.whatsapp_client import WhatsAppClient
from app.langchain_server import LangChainServer

# previous starting command: gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.webhook:app

app = FastAPI()

# Outside the endpoint function
langch_instances = {}

WHATSAPP_HOOK_TOKEN = os.environ.get("WHATSAPP_HOOK_TOKEN")
# Outside the class, initialize the OpenAI API key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


@app.get("/")
def I_am_alive():
    return "I am alive!!"


@app.get("/webhook/")
def subscribe(request: Request):
    print("subscribe is being called")
    if request.query_params.get('hub.verify_token') == WHATSAPP_HOOK_TOKEN:
        return int(request.query_params.get('hub.challenge'))
    return "Authentication failed. Invalid Token."


@app.post("/webhook/")
async def process_notifications(request: Request):
    wtsapp_client = WhatsAppClient()
    data = await request.json()
    print("We received " + str(data))
    response = wtsapp_client.process_notification(data)
    if response["statusCode"] == 200:
        if response["body"] and response["from_no"]:
            from_no = response["from_no"]
            print("\nfrom_no is:" + from_no)


            # Print the keys in the dictionary
            print("Current keys in langch_instances:", list(langch_instances.keys()))

            # Check if an instance already exists for the phone number
            if from_no in langch_instances:
                langch_instance = langch_instances[from_no]
                print(f"Reusing existing LangChainServer instance for {from_no}")
            else:
                # Create a new instance if not already present
                langch_instance = LangChainServer(OPENAI_API_KEY)  # Replace with your instance creation logic
                langch_instances[from_no] = langch_instance
                print(f"Creating a new LangChainServer instance for {from_no}")

            # Use the stored instance to generate a reply
            langch_instance = langch_instances[from_no]
            reply = langch_instance.process_user_message(user_input=response["body"],
                                                         all_messages=[])

            print("\nreply is:" + reply)

            print("\nbuffer memory is:")
            print(langch_instance.memory_buffer())

            # Send the reply back to WhatsApp
            wtsapp_client.send_text_message(message=reply, phone_number=from_no)
            print("\nreply is sent to WhatsApp cloud:" + str(response))

    return {"status": "success"}, 200