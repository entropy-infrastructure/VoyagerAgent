from action import ActionAgent
import os

openai_api_key=os.getenv("OPENAI_API_KEY")

def main():
    # set openai api key
    os.environ["OPENAI_API_KEY"] = openai_api_key

    action_agent = ActionAgent()

    task = "Create ansible inventory builder for to install apache"

    system_message = action_agent.render_system_message(skills={"ansible":[],"pulumi":[]})
    human_message = action_agent.render_human_message(
        events=[],
        code="",
        task=task,
        context="",
        critique="",
    )

    messages = [system_message, human_message]

    print(action_agent.llm(messages).content)


if __name__ == "__main__":
    main()
