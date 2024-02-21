

from voyager.env.extract_code_prompt import execute
from voyager.env.extract_code_prompt import write_files


class VoyagerEnv:

    def __init__(self):
        pass

    def write_prompt(self, prompt):
        return write_files(prompt)

    def execute(self):
        return execute()