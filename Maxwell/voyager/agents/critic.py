from voyager.prompts import load_prompt
from voyager.utils.json_utils import fix_and_parse_json
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

class CriticAgent:
    def __init__(
        self,
        model_name="gpt-3.5-turbo",
        temperature=0,
        request_timout=120,
        mode="auto",
    ):
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            request_timeout=request_timout,
        )
        assert mode in ["auto", "manual"]
        self.mode = mode

    """
    standard, each one has a sys message method and a human message method
    """
    def render_system_message(self):
        system_message = SystemMessage(content=load_prompt("critic"))
        return system_message

    """
    get observation, if errors in env events -> return none

    flesh out observation string with details, task, context, and chest observation
    return observation
    """
    def render_human_message(self, errors, task, context=None, code=None):

        observation = ""

        observation += f"Task: {task}\n\n"

        if context:
            observation += f"Context: {context}\n\n"
        else:
            observation += f"Context: None\n\n"
        if code:
            observation += f"Code: ```python\n{code}```\n\n"
        else:
            observation += f"Context: None\n\n"

        # print(f"\033[31m****Critic Agent human message****\n{observation}\033[0m")
        return HumanMessage(content=observation)

    """
      manual confirmation of task success -> good
    """
    def human_check_task_success(self):
        confirmed = False
        success = False
        critique = ""
        while not confirmed:
            success = input("Success? (y/n)")
            success = success.lower() == "y"
            critique = input("Enter your critique:")
            print(f"Success: {success}\nCritique: {critique}")
            confirmed = input("Confirm? (y/n)") in ["y", ""]
        return success, critique

    """
      pass in messages, get response
      if response["success"] is true -> return y/n succeeded + critique
    """
    def ai_check_task_success(self, messages, max_retries=5):
        if max_retries == 0:
            print(
                "\033[31mFailed to parse Critic Agent response. Consider updating your prompt.\033[0m"
            )
            return False, ""

        if messages[1] is None:
            return False, ""

        critic = self.llm(messages).content
        print(f"\033[31m****Critic Agent ai message****\n{critic}\033[0m")
        try:
            response = fix_and_parse_json(critic)
            assert response["success"] in [True, False]
            if "critique" not in response:
                response["critique"] = ""
            return response["success"], response["critique"]
        except Exception as e:
            print(f"\033[31mError parsing critic response: {e} Trying again!\033[0m")
            return self.ai_check_task_success(
                messages=messages,
                max_retries=max_retries - 1,
            )

    #TODO
    # Implement preflight checks

    """
    gets observation from human message
    gets sys mesage + human message
    calls respective checker function -> how does it identify task? i guess task is given
    """
    def check_task_success(
        self, errors, task, context, code, max_retries=5
    ):

        if self.mode == "manual":
            return self.human_check_task_success()
        elif self.mode == "auto":

            human_message = self.render_human_message(
                errors=errors,
                task=task,
                context=context,
                code=code
            )

            messages = [
                self.render_system_message(),
                human_message,
            ]

            #TODO
            # Check Errors
            # Check Task with Critic model

            return self.ai_check_task_success(
                messages=messages, max_retries=max_retries
            )
        else:
            raise ValueError(f"Invalid critic agent mode: {self.mode}")
