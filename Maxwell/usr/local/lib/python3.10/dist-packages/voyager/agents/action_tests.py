from action import ActionAgent
import os

openai_api_key=os.getenv("OPENAI_API_KEY")

def main():
    # set openai api key
    os.environ["OPENAI_API_KEY"] = openai_api_key

    agent = ActionAgent()

    sys_msg = agent.render_system_message()
    print(sys_msg)


if __name__ == "__main__":
    main()
