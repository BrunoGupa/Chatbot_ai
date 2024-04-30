import warnings

warnings.filterwarnings('ignore')

from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationTokenBufferMemory

import openai

import json


class LangChainServer:
    def __init__(self, openai_api_key):
        openai.api_key = openai_api_key
        self.llm = ChatOpenAI(temperature=0.0)
        self.memory = ConversationTokenBufferMemory(llm=self.llm, max_token_limit=200)

        self.products = self.get_products()
        self.api_key = openai_api_key


    def memory_buffer(self):
        return self.memory.load_memory_variables({})

    def get_completion_from_messages(self, messages, model="gpt-3.5-turbo", temperature=0, max_tokens=500):
        openai.api_key = self.api_key
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message["content"]

    def get_products_and_category(self):
        products_and_category = '''
            Our Menu:

            Meals:
            Vegan Cheese Quesadilla
            Mushroom Quesadilla
            Black Bean Quesadilla

            Drinks:
            Black Tea
            Green Tea
            
            '''
        return products_and_category

    def find_category_and_product_only(self, user_input, products_and_category):
        delimiter = "####"
        system_message = f"""
        You will be provided with customer service queries. \
        The customer service query will be delimited with \
        {delimiter} characters.
        Output a python list of objects, where each object has \
        the following format:
            'category': <one of meals or Drinks>,
        OR
            'products': <a list of products that must \
            be found in the allowed products below>

        Where the categories and products must be found in \
        the customer service query.
        If a product is mentioned, it must be associated with \
        the correct category in the allowed products list below.
        If no products or categories are found, output an \
        empty list.

        Allowed products: 

        {products_and_category}

        Only output the list of objects, with nothing else.

        """

        messages = [
            {'role': 'system',
             'content': system_message},
            {'role': 'user',
             'content': f"{delimiter}{user_input}{delimiter}"},
        ]
        return self.get_completion_from_messages(messages)

    # insert a dictionary in this class caled products

    def get_products(self):
        return {
            "Vegan Cheese Quesadilla": {
                "name": "Vegan Cheese Quesadilla",
                "category": "Meals",
                "ingredients": ["Vegan cheese", "Whole wheat tortilla", "Mixed vegetables"],
                "description": "Our Vegan Cheese Quesadilla is a delightful blend of savory vegan cheese, fresh mixed vegetables, all wrapped in a warm whole wheat tortilla. It's a perfect choice for vegans and cheese lovers alike!",
                "price": '$8.99',
            },
            "Mushroom Quesadilla": {
                "name": "Mushroom Quesadilla",
                "category": "Meals",
                "ingredients": ["Sauteed mushrooms", "Jack cheese", "Flour tortilla"],
                "description": "Indulge in the rich flavors of our Mushroom Quesadilla! Made with savory sauteed mushrooms, melted jack cheese, and wrapped in a soft flour tortilla, it's a taste sensation you won't want to miss.",
                "price": '$9.99',
            },
            "Black Bean Quesadilla": {
                "name": "Black Bean Quesadilla",
                "category": "Meals",
                "ingredients": ["Black beans", "Cheddar cheese", "Corn tortilla"],
                "description": "Savor the taste of our Black Bean Quesadilla! Loaded with hearty black beans, melted cheddar cheese, and nestled in a crispy corn tortilla, it's a satisfying meal that's bursting with flavor.",
                "price": '$7.99',
            },
            "Black Tea": {
                "name": "Black Tea",
                "category": "Drinks",
                "description": "Enjoy the rich and robust flavor of our Black Tea. Sourced from the finest tea leaves, it's a perfect choice for a refreshing beverage anytime of the day.",
                "price": '$2.50',
            },
            "Green Tea": {
                "name": "Green Tea",
                "category": "Drinks",
                "description": "Savor the delicate and refreshing taste of our Green Tea. Packed with antioxidants and nutrients, it's a healthy and revitalizing choice to accompany your meal.",
                "price": '$2.50',
            },
        }

    def get_product_by_name(self, name):
        return self.products.get(name, None)

    def get_products_by_category(self, category):
        return [product for product in self.products.values() if product["category"] == category]

    def read_string_to_list(self, input_string):
        if input_string is None:
            return None

        try:
            input_string = input_string.replace("'", "\"")  # Replace single quotes with double quotes for valid JSON
            data = json.loads(input_string)
            return data
        except json.JSONDecodeError:
            print("Error: Invalid JSON string")
            return None

    def generate_output_string(self, data_list):
        output_string = ""

        if data_list is None:
            return output_string

        for data in data_list:
            try:
                if "products" in data:
                    products_list = data["products"]
                    for product_name in products_list:
                        product = self.get_product_by_name(product_name)
                        if product:
                            output_string += json.dumps(product, indent=4) + "\n"
                        else:
                            print(f"Error: Product '{product_name}' not found")
                elif "category" in data:
                    category_name = data["category"]
                    category_products = self.get_products_by_category(category_name)
                    for product in category_products:
                        output_string += json.dumps(product, indent=4) + "\n"
                else:
                    print("Error: Invalid object format")
            except Exception as e:
                print(f"Error: {e}")

        return output_string

    def moderation(self, input_text):
        openai.api_key = self.api_key
        response = openai.Moderation.create(input=input_text)
        moderation_output = response["results"][0]
        return moderation_output["flagged"]

    def process_user_message(self, user_input, all_messages, debug=True):
        delimiter = "```"

        # Step 1: Check input to see if it flags the Moderation API or is a prompt injection
        if self.moderation(user_input):
            print("Step 1: Input flagged by Moderation API.")
            return "Sorry, we cannot process this request."

        if debug: print("Step 1: Input passed moderation check.")

        category_and_product_response = self.find_category_and_product_only(user_input,
                                                                            self.get_products_and_category())
        if debug: print(category_and_product_response)

        # Step 2: Extract the list of products
        category_and_product_list = self.read_string_to_list(category_and_product_response)

        if debug: print(f"Step 2: Extracted list of products.")

        # Step 3: If products are found, look them up
        product_information = self.generate_output_string(category_and_product_list)

        if debug: print("Step 3: Looked up product information.")

        # Step 4: Answer the user question
        system_message = f"""
        You are a customer service assistant for Quesadilla AI. \
        Respond in a friendly and helpful tone, with concise answers. \
        Make sure to ask the user relevant follow-up questions. \
         """
        messages = [
            {'role': 'system', 'content': system_message},
            {'role': 'user', 'content': f"{delimiter}{user_input}{delimiter}"},
            {'role': 'assistant', 'content': f"Relevant product information:\n{product_information}"}
        ]

        final_response = self.get_completion_from_messages(all_messages + messages)
        if debug: print("Step 4: Generated response to user question.")

        # Step 5: Put the answer through the Moderation API
        response = openai.Moderation.create(input=final_response)
        moderation_output = response["results"][0]

        if moderation_output["flagged"]:
            if debug: print("Step 5: Response flagged by Moderation API.")
            return "Sorry, we cannot provide this information."

        if debug: print("Step 5: Response passed moderation check.")

        # Step 6: Ask the model if the response answers the initial user query well
        user_message = f"""
        Customer message: {delimiter}{user_input}{delimiter}
        Agent response: {delimiter}{final_response}{delimiter}

        Does the response sufficiently answer the question?
        """
        messages = [
            {'role': 'system', 'content': system_message},
            {'role': 'user', 'content': user_message}
        ]
        evaluation_response = self.get_completion_from_messages(messages)
        if debug: print("Step 6: Model evaluated the response.")

        # Step 7: If yes, use this answer; if not, say that you will connect the user to a human
        if "Y" in evaluation_response:  # Using "in" instead of "==" to be safer for model output variation (e.g., "Y." or "Yes")
            if debug: print("Step 7: Model approved the response.")
            # To save context in the memory (offline process)
            self.memory.save_context({"input": f"{delimiter}{user_input}{delimiter}"},
                                     {"output": f"{delimiter}{final_response}{delimiter}"})
            if debug: print(self.memory.load_memory_variables({}))

            return final_response
        else:
            if debug: print("Step 7: Model disapproved the response.")
            neg_str = "I'm unable to provide the information you're looking for. I'll connect you with a human representative for further assistance."
            # To save context in the memory (offline process)
            self.memory.save_context({"input": f"{delimiter}{user_input}{delimiter}"},
                                     {"output": f"{delimiter}{neg_str}{delimiter}"})
            if debug: print(self.memory.load_memory_variables({}))

            return neg_str
