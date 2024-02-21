from curriculum import CurriculumAgent
import os

openai_api_key=os.getenv("OPENAI_API_KEY")

def main():
    # set openai api key
    os.environ["OPENAI_API_KEY"] = openai_api_key

    cirriculum_agent = CurriculumAgent()

    task = "Create an apache server"


    # print(cirriculum_agent.render_human_message())

    print(cirriculum_agent.propose_next_task())


if __name__ == "__main__":
    main()
