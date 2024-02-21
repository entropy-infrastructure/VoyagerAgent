import re
import time

import voyager.utils as U
# from javascript import require
from langchain.chat_models import ChatOpenAI
from langchain.prompts import SystemMessagePromptTemplate
from langchain.schema import AIMessage, HumanMessage, SystemMessage

from voyager.prompts import load_prompt
from voyager.control_primitives_context import load_control_primitives_context

"""
ActionAgent class

Stores chest memory

"""
class ActionAgent:
    def __init__(
        self,
        model_name="gpt-3.5-turbo",
        temperature=0,
        request_timout=120,
        ckpt_dir="ckpt",
        chat_log=True,
        execution_error=True,
    ):
        self.ckpt_dir = ckpt_dir
        self.chat_log = chat_log
        self.execution_error = execution_error
        self.model_name = model_name

        # self.base_skills = [
        #     "exploreUntil",
            # "mineBlock",
            # "craftItem",
            # "placeItem",
            # "smeltItem",
            # "killMob",
        # ]

        # if not self.model_name == "gpt-3.5-turbo":
        #     self.base_skills += [
        #         "useChest",
        #         "mineflayer",
        #     ]

        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            request_timeout=request_timout,
        )

    """
    loads action template
    base skills hardcoded, if using gpt4 add useCHest and mineflayer as skills

    uses double newlines to load a list of skills + the base skills into a string called programs

    formats the system prompt with the available skills
    """

    #TODO: Test primitive loading
    def render_system_message(self, skills={"ansible":[], "pulumi":[]}):
        system_template = load_prompt("action_template")

        ansible_programs = "\n\n".join(skills["ansible"])
        pulumi_programs = "\n\n".join(skills["pulumi"])
        response_format = load_prompt("action_response_format")
        system_message_prompt = SystemMessagePromptTemplate.from_template(
            system_template
        )
        system_message = system_message_prompt.format(response_format=response_format
        )
        assert isinstance(system_message, SystemMessage)
        return system_message


    """
    takes events and adds them to chat history or error history. else, sets a bunch of variables (the last one must be observe)

    code is generated, uses previous code as input (last round == previous attempt at task)

    observation = previous attempt code + error messages + chat log + all observation vars + task + context + critique
    """
    def render_human_message(
        self, *, events, code="", task="", context="", critique=""
    ):
        chat_messages = []
        error_messages = []
        observation = ""
        # assert events[-1][0] == "observe", "Last event must be observe"
        for i, (event_type, event) in enumerate(events):
            if event_type == "onChat":
                chat_messages.append(event["onChat"])
            elif event_type == "onError":
                error_messages.append(event["onError"])
            #TODO
            # Implement observation

            # elif event_type == "observe":
                # biome = event["status"]["biome"]
                # time_of_day = event["status"]["timeOfDay"]
                # health = event["status"]["health"]
                # hunger = event["status"]["food"]
                # position = event["status"]["position"]
                # equipment = event["status"]["equipment"]
                # inventory_used = event["status"]["inventoryUsed"]
                # inventory = event["inventory"]
                # assert i == len(events) - 1, "observe must be the last event"

        observation += f"Task: {task}\n\n"

        if context:
            observation += f"Context: {context}\n\n"
        else:
            observation += f"Context: None\n\n"

        if code:
            observation += f"Code from the last round:\n{code}\n\n"
        else:
            observation += f"Code from the last round: No code in the first round\n\n"

        #ExecutionErrorBlock
        if self.execution_error:
            if error_messages:
                error = "\n".join(error_messages)
                observation += f"Execution error:\n{error}\n\n"
            else:
                observation += f"Execution error: No error\n\n"

        #CritiqueBlock
        if critique:
            observation += f"Critique: {critique}\n\n"
        else:
            observation += f"Critique: None\n\n"

        #ChatLogBlock
        if self.chat_log:
            if chat_messages:
                chat_log = "\n".join(chat_messages)
                observation += f"Chat log: {chat_log}\n\n"
            else:
                observation += f"Chat log: None\n\n"

        return HumanMessage(content=observation)

    """
    filter identifies items via regex that require things

    join list of stuff and return sum total of needed inventory
    """
    def summarize_chatlog(self, events):
        def filter_item(message: str):
            craft_pattern = r"I cannot make \w+ because I need: (.*)"
            craft_pattern2 = (
                r"I cannot make \w+ because there is no crafting table nearby"
            )
            mine_pattern = r"I need at least a (.*) to mine \w+!"
            if re.match(craft_pattern, message):
                return re.match(craft_pattern, message).groups()[0]
            elif re.match(craft_pattern2, message):
                return "a nearby crafting table"
            elif re.match(mine_pattern, message):
                return re.match(mine_pattern, message).groups()[0]
            else:
                return ""

        chatlog = set()
        for event_type, event in events:
            if event_type == "onChat":
                item = filter_item(event["onChat"])
                if item:
                    chatlog.add(item)
        return "I also need " + ", ".join(chatlog) + "." if chatlog else ""
