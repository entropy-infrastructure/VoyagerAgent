from __future__ import annotations

import random
import re

import voyager.utils as U
from voyager.prompts import load_prompt
from voyager.utils.json_utils import fix_and_parse_json
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.schema import HumanMessage, SystemMessage
from langchain.vectorstores import Chroma


"""
K: Cirriculum stores failed and successful tasks
"""

class CurriculumAgent:
    def __init__(
        self,
        model_name="gpt-3.5-turbo",
        temperature=0,
        qa_model_name="gpt-3.5-turbo",
        qa_temperature=0,
        request_timout=120,
        ckpt_dir="ckpt",
        resume=False,
        mode="auto",
        warm_up=None,
        core_inventory_items: str | None = None,
    ):
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            request_timeout=request_timout,
        )

        self.qa_llm = ChatOpenAI(
            model_name=qa_model_name,
            temperature=qa_temperature,
            request_timeout=request_timout,
        )

        assert mode in [
            "auto",
            "manual",
        ], f"mode {mode} not supported"
        self.mode = mode
        self.ckpt_dir = ckpt_dir
        U.f_mkdir(f"{ckpt_dir}/curriculum/vectordb")
        if resume:
            print(f"\033[35mLoading Curriculum Agent from {ckpt_dir}/curriculum\033[0m")
            self.completed_tasks = U.load_json(
                f"{ckpt_dir}/curriculum/completed_tasks.json"
            )
            self.failed_tasks = U.load_json(f"{ckpt_dir}/curriculum/failed_tasks.json")
            self.qa_cache = U.load_json(f"{ckpt_dir}/curriculum/qa_cache.json")
        else:
            self.completed_tasks = []
            self.failed_tasks = []
            self.qa_cache = {}

        # vectordb for qa cache
        self.qa_cache_questions_vectordb = Chroma(
            collection_name="qa_cache_questions_vectordb",
            embedding_function=OpenAIEmbeddings(),
            persist_directory=f"{ckpt_dir}/curriculum/vectordb",
        )

        assert self.qa_cache_questions_vectordb._collection.count() == len(
            self.qa_cache
        ), (
            f"Curriculum Agent's qa cache question vectordb is not synced with qa_cache.json.\n"
            f"There are {self.qa_cache_questions_vectordb._collection.count()} questions in vectordb "
            f"but {len(self.qa_cache)} questions in qa_cache.json.\n"
            f"Did you set resume=False when initializing the agent?\n"
            f"You may need to manually delete the qa cache question vectordb directory for running from scratch.\n"
        )

        # if warm up not defined, initialize it as a dict, else, initialize all the missing value as a default value
        if not warm_up:
            warm_up = self.default_warmup
        self.warm_up = {}

        for key in self.curriculum_observations:
            self.warm_up[key] = warm_up.get(key, self.default_warmup[key])

        self.warm_up["completed_tasks"] = 0
        self.warm_up["failed_tasks"] = 0

    """
    K: Initializes default list. 
    """
    @property
    def default_warmup(self):
        return {
            "context": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
        }

    @property
    def curriculum_observations(self):
        return [
            "context",
            "completed_tasks",
            "failed_tasks",
        ]

    """
    k: returns length of list of completed tasks
    """
    @property
    def progress(self):
        return len(self.completed_tasks)

    """
    use langchain to return the system prompt. Prompt is loaded from the "prompts" folder with the key cirriculum"
    """
    def render_system_message(self):
        system_message = SystemMessage(content=load_prompt("curriculum"))
        assert isinstance(system_message, SystemMessage)
        return system_message

    """
    K: Asserts that the last event before continuting the next 'Step' is an observation event (Steps are sets of events +        processing). In the case that it is, it basically takes a bunch of environment data and renders a dictionary of           that data in a consistent string format
    """
    def render_observation(self):
        # assert events[-1][0] == "observe", "Last event must be observe"
        # event = events[-1][1]
        # biome = event["status"]["biome"]
        # time_of_day = event["status"]["timeOfDay"]
        # voxels = event["voxels"]
        # block_records = event["blockRecords"]
        # entities = event["status"]["entities"]
        # health = event["status"]["health"]
        # hunger = event["status"]["food"]
        # position = event["status"]["position"]
        # equipment = event["status"]["equipment"]
        # inventory_used = event["status"]["inventoryUsed"]
        # inventory = event["inventory"]

        """
        Other blocks is a record of recently seen blocks. Voxels is a set of nearby blocks, here calculates the diff
        
        Here lets use deployment history
        """
        # other_blocks = ", ".join(
        #     list(
        #         set(block_records).difference(set(voxels).union(set(inventory.keys())))
        #     )
        # )
        #
        # other_blocks = other_blocks if other_blocks else "None"
        #
        # nearby_entities = (
        #     ", ".join([k for k, v in sorted(entities.items(), key=lambda x: x[1])])
        #     if entities
        #     else "None"
        # )


        """
        K: This is takes the local list of completed tasks and failed tasks and turns it into a string
        """
        completed_tasks = (
            ", ".join(self.completed_tasks) if self.completed_tasks else "None"
        )
        failed_tasks = ", ".join(self.failed_tasks) if self.failed_tasks else "None"


        """
        this calculates the inventory state to determine if progress is less than that required for the warmup period.
        
        Default set of 
        
        This implies that they have some minimum state before actually training on a cirriculum. IE it must explore for a minimum amount prior to doing anything.
        """
        # # filter out optional inventory items if required
        # if self.progress < self.warm_up["optional_inventory_items"]:
        #     inventory = {
        #         k: v
        #         for k, v in inventory.items()
        #         if self._core_inv_items_regex.search(k) is not None
        #     }

        observation = {
            "context": "",
            "completed_tasks": f"Completed tasks so far: {completed_tasks}\n\n",
            "failed_tasks": f"Failed tasks that are too hard: {failed_tasks}\n\n",
        }
        return observation

    """
    K:
    first render observation -> create string dict describing env
    if progress is enough, develop question answer pairs abt env
    for each qa pair, if it has actual information, add it to env context
    use a probability to determine if which of the total observation keys should be included
      if the key was already in the warm up dict and has been surpassed, then assign a probability less than 1 to include       it in the env human message
    """
    def render_human_message(self):
        content = ""
        observation = self.render_observation()
        if self.progress >= self.warm_up["context"]:
            questions, answers = self.run_qa()
            i = 1
            for question, answer in zip(questions, answers):
                if "Answer: Unknown" in answer or "language model" in answer:
                    continue
                observation["context"] += f"Question {i}: {question}\n"
                observation["context"] += f"{answer}\n\n"
                i += 1
                if i > 5:
                    break


        #Potential Nonetype error here
        for key in self.curriculum_observations:
            if self.progress >= self.warm_up[key]:
                if self.warm_up[key] != 0:
                    should_include = random.random() < 0.8
                else:
                    should_include = True
                if should_include:
                    content += observation[key]

        print(f"\033[35m****Curriculum Agent human message****\n{content}\033[0m")
        return HumanMessage(content=content)

    """
    Chest observation is a list of chests where chest has an id and a position in text
    
    1. if init -> set base task
    2. if inventory almost full, hardcode task to deposit in nearest chest
    3.   If no chest, hardcode task to build or place a chest
    4. if inventory not almost full, generate task
    5. to generate task, render sys message, and render human message (do all the QA crap)
    """
    def propose_next_task(self, max_retries=5):
        if self.progress == 0 and self.mode == "auto":
            task = "Deploy an instance on AWS and copy the current directory over to it, build docker image from the directory, and run the docker image as a container."
            context = "You can deploy one instance of any size onto AWS. Use it in pulumi with aws.ec2 "
            return task, context

        if self.progress == 1 and self.mode == "auto":
            task = "Deploy an instance on AWS and copy the current directory over to it, build docker image from the directory, and run the docker image as a container."
            context = "You can deploy one instance of any size onto AWS. Use it in pulumi with aws.ec2"
            return task, context


        if self.mode == "auto":
            messages = [
                self.render_system_message(),
                self.render_human_message(),
            ]

            return self.propose_next_ai_task(messages=messages, max_retries=max_retries)
        elif self.mode == "manual":
            return self.propose_next_manual_task()
        else:
            raise ValueError(f"Invalid curriculum agent mode: {self.mode}")

    """
      Run LLM with sys and human messages from propose next task
      Try to parse the the output into a task.
      Reframes task as QA pair for the target task as the task "context"
      return task and QA context pair
      On exception, recursively reduces max retries and defaults to 5
    """
    def propose_next_ai_task(self, *, messages, max_retries=5):
        if max_retries == 0:
            raise RuntimeError("Max retries reached, failed to propose ai task.")
        curriculum = self.llm(messages).content
        print(f"\033[31m****Curriculum Agent ai message****\n{curriculum}\033[0m")
        try:
            response = self.parse_ai_message(curriculum)
            assert "next_task" in response
            context = self.get_task_context(response["next_task"])
            return response["next_task"], context
        except Exception as e:
            print(
                f"\033[35mError parsing curriculum response: {e}. Trying again!\033[0m"
            )
            return self.propose_next_ai_task(
                messages=messages,
                max_retries=max_retries - 1,
            )

    def parse_ai_message(self, message):
        task = ""
        for line in message.split("\n"):
            if line.startswith("Task:"):
                task = line[5:].replace(".", "").strip()
        assert task, "Task not found in Curriculum Agent response"
        return {"next_task": task}

    """
    Get manual task from user
    """
    def propose_next_manual_task(self):
        confirmed = False
        task, context = "", ""
        while not confirmed:
            task = input("Enter task: ")
            context = input("Enter context: ")
            print(f"Task: {task}\nContext: {context}")
            confirmed = input("Confirm? (y/n)").lower() in ["y", ""]
        return task, context

    def update_exploration_progress(self, info):
        task = info["task"]
        if info["success"]:
            print(f"\033[35mCompleted task {task}.\033[0m")
            self.completed_tasks.append(task)
        else:
            print(
                f"\033[35mFailed to complete task {task}. Skipping to next task.\033[0m"
            )
            self.failed_tasks.append(task)

        # clean up tasks and dump to disk
        self.clean_up_tasks()

    def clean_up_tasks(self):
        updated_completed_tasks = []
        # record repeated failed tasks
        updated_failed_tasks = self.failed_tasks
        # dedup but keep order
        for task in self.completed_tasks:
            if task not in updated_completed_tasks:
                updated_completed_tasks.append(task)

        # remove completed tasks from failed tasks
        for task in updated_completed_tasks:
            while task in updated_failed_tasks:
                updated_failed_tasks.remove(task)

        self.completed_tasks = updated_completed_tasks
        self.failed_tasks = updated_failed_tasks

        # dump to json
        U.dump_json(
            self.completed_tasks, f"{self.ckpt_dir}/curriculum/completed_tasks.json"
        )
        U.dump_json(self.failed_tasks, f"{self.ckpt_dir}/curriculum/failed_tasks.json")

    """
      Renders sys decomp message + human observation message + target task -> attemps to get llm to output decomp
    """
    def decompose_task(self, task, events):
        messages = [
            SystemMessage(
                content=load_prompt("curriculum_task_decomposition"),
            ),
            self.render_human_message(events=events, chest_observation=""),
            HumanMessage(content=f"Final task: {task}"),
        ]
        print(
            f"\033[31m****Curriculum Agent task decomposition****\nFinal task: {task}\033[0m"
        )
        response = self.llm(messages).content
        print(f"\033[31m****Curriculum Agent task decomposition****\n{response}\033[0m")
        return fix_and_parse_json(response)



    """
    1. Generate Questions
    2. For each, get the nearest QA pair (if close enough -> use cached pair)
    3. For each question without an answer, get an answer. Make sure question is not in QACache
    4.       Add the question to QACache dict (with answer) and QACache vector db
    5. save the QA cache as json
    6. persist the vector db
    7. add q's and a's to q list and a list respectively
    8. Return list of qs and list of a's
    """
    def run_qa(self):

        questions_new, _, registry_questions, _ = self.run_qa_step1_ask_questions() #TODO need to pass keywords
        questions = []
        answers = []
        for question in questions_new:
            if self.qa_cache_questions_vectordb._collection.count() > 0:
                docs_and_scores = (
                    self.qa_cache_questions_vectordb.similarity_search_with_score(
                        question, k=1
                    )
                )
                if docs_and_scores and docs_and_scores[0][1] < 0.05:
                    question_cached = docs_and_scores[0][0].page_content
                    assert question_cached in self.qa_cache
                    answer_cached = self.qa_cache[question_cached]
                    questions.append(question_cached)
                    answers.append(answer_cached)
                    continue
            answer = self.run_qa_step2_answer_questions(question=question)
            assert question not in self.qa_cache
            self.qa_cache[question] = answer
            self.qa_cache_questions_vectordb.add_texts(
                texts=[question],
            )
            U.dump_json(self.qa_cache, f"{self.ckpt_dir}/curriculum/qa_cache.json")
            self.qa_cache_questions_vectordb.persist()
            questions.append(question)
            answers.append(answer)
        assert len(questions_new) == len(questions) == len(answers)
        return questions, answers

    """
    1. create clean question from task to ask gpt (Strangely does not check for similarity)
    2. throw QA into cache dict and Q into vector db
    3. return string with Q for task on one line, and answer on next (this is one thing that builds up model knowledge)
    """
    def get_task_context(self, task):
        # if include ore in question, gpt will try to use tool with skill touch enhancement to mine
        question = (
            f"How to {task.replace('_', ' ').replace(' ore', '').replace(' ores', '').replace('.', '').strip().lower()}"
            f" in AWS?"
        )
        if question in self.qa_cache:
            answer = self.qa_cache[question]
        else:
            answer = self.run_qa_step2_answer_questions(question=question)
            self.qa_cache[question] = answer
            self.qa_cache_questions_vectordb.add_texts(
                texts=[question],
            )
            U.dump_json(self.qa_cache, f"{self.ckpt_dir}/curriculum/qa_cache.json")
            self.qa_cache_questions_vectordb.persist()
        context = f"Question: {question}\n{answer}"
        return context

    def render_system_message_qa_step1_ask_questions(self):
        return SystemMessage(content=load_prompt("curriculum_qa_step1_ask_questions"))


    """
    Render observation
    for key in object, \n observation
    create langchain human message from string (with env data)
    """
    def render_human_message_qa_step1_ask_questions(self):
        observation = self.render_observation()
        content = ""
        for key in self.curriculum_observations:
            content += observation[key]
        return HumanMessage(content=content)

    
    """
    1. Sets up stock questions + concept pairs
    2. Renders a QA prompt as a sys message
    3. Renders an env observation block as a human message
    4. Gets questions + concept pirs from the sys + human message prompt
    5. returns list of questions and concepts
    
    
    Keywords is a list of keywords
    """
    def run_qa_step1_ask_questions(self, keywords=[]):
        # biome = events[-1][1]["status"]["biome"].replace("_", " ")

        kw = ", ".join(keywords)

        registry_questions = [
            f"What are the docker containers that I can use given these keywords: {kw}?",
            f"What are the AMIs that I can find in the AWS registry for these keywords: {kw}?"
        ]
        registry_concepts = ["Docker", "AWS AMI"]

        questions = []
        concepts = []

        messages = [
            self.render_system_message_qa_step1_ask_questions(), #Render sys message
            self.render_human_message_qa_step1_ask_questions(),  #Render observation context + task
        ]
        qa_response = self.qa_llm(messages).content
        try:
            # Regex pattern to extract question and concept pairs
            pattern = r"Question \d+: (.+)\nConcept \d+: (.+)"
            # Extracting all question and concept pairs from the text
            pairs = re.findall(pattern, qa_response)
            # Storing each question and concept in separate lists
            questions_new = [pair[0] for pair in pairs]
            concepts_new = [pair[1] for pair in pairs]
            assert len(questions_new) == len(concepts_new)
            questions.extend(questions_new)
            concepts.extend(concepts_new)
        except Exception as e:
            print(
                f"\033[35mError parsing curriculum response for "
                f"QA step 1 ask questions: {e}.\033[0m"
            )
        return questions, concepts, registry_questions, registry_concepts

    def render_system_message_qa_step2_answer_questions(self):
        return SystemMessage(
            content=load_prompt("curriculum_qa_step2_answer_questions")
        )

    def render_human_message_qa_step2_answer_questions(self, question):
        content = f"Question: {question}"
        return HumanMessage(content=content)

    """
    Load QA prompts, pass question -> generate answer
    """
    def run_qa_step2_answer_questions(self, question):
        messages = [
            self.render_system_message_qa_step2_answer_questions(),
            self.render_human_message_qa_step2_answer_questions(question=question),
        ]
        print(f"\033[35mCurriculum Agent Question: {question}\033[0m")
        qa_answer = self.qa_llm(messages).content
        print(f"\033[31mCurriculum Agent {qa_answer}\033[0m")
        return qa_answer
