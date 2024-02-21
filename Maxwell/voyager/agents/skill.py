import os

import voyager.utils as U
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.schema import HumanMessage, SystemMessage
from langchain.vectorstores import Chroma

from voyager.prompts import load_prompt
from voyager.control_primitives import load_control_primitives


class SkillManager:
    def __init__(
        self,
        model_name="gpt-3.5-turbo",
        temperature=0,
        retrieval_top_k=5,
        request_timout=120,
        ckpt_dir="ckpt",
        resume=False,
    ):
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            request_timeout=request_timout,
        )
        U.f_mkdir(f"{ckpt_dir}/skill/pulumi/code")
        U.f_mkdir(f"{ckpt_dir}/skill/pulumi/description")
        U.f_mkdir(f"{ckpt_dir}/skill/pulumi/vectordb")

        U.f_mkdir(f"{ckpt_dir}/skill/ansible/code")
        U.f_mkdir(f"{ckpt_dir}/skill/ansible/description")
        U.f_mkdir(f"{ckpt_dir}/skill/ansible/vectordb")
        # programs for env execution

        """
          Control primitives are simple py programs to control the env
        """
       
        self.control_primitives = load_control_primitives() #Just does a default directory scan
        if resume:
            print(f"\033[33mLoading Skill Manager from {ckpt_dir}/skill\033[0m")

            """
              load json file for skills
            """
            self.pulumi_skills = U.load_json(f"{ckpt_dir}/skill/pulumi/skills.json")
            self.ansible_skills = U.load_json(f"{ckpt_dir}/skill/ansible/skills.json")
            self.skills = {
                "pulumi": self.pulumi_skills,
                "ansible": self.ansible_skills,
            }
        else:
            self.skills = {
                "pulumi":{},
                "ansible":{}
            }

        """
        Top k = number of items to retrieve upon skill retrieval from chroma DB
        """
        self.retrieval_top_k = retrieval_top_k
        self.ckpt_dir = ckpt_dir

        """
        Create vector DB
        Vector DB syncing with JSON skill library
        """
        self.pulumi_vectordb = Chroma(
            collection_name="pulumi_skill_vectordb",
            embedding_function=OpenAIEmbeddings(),
            persist_directory=f"{ckpt_dir}/skill/vectordb/p",
        )
        self.ansible_vectordb = Chroma(
            collection_name="ansible_skill_vectordb",
            embedding_function=OpenAIEmbeddings(),
            persist_directory=f"{ckpt_dir}/skill/vectordb/a",
        )
        assert self.ansible_vectordb._collection.count() == len(self.skills["ansible"]), (
            f"Skill Manager's vectordb is not synced with skills.json.\n"
            f"There are {self.ansible_vectordb._collection.count()} skills in vectordb but {len(self.skills['ansible'])} skills in skills.json.\n"
            f"Did you set resume=False when initializing the manager?\n"
            f"You may need to manually delete the vectordb directory for running from scratch."
        )
        assert self.pulumi_vectordb._collection.count() == len(self.skills["pulumi"]), (
            f"Skill Manager's vectordb is not synced with skills.json.\n"
            f"There are {self.pulumi_vectordb._collection.count()} skills in vectordb but {len(self.skills['pulumi'])} skills in skills.json.\n"
            f"Did you set resume=False when initializing the manager?\n"
            f"You may need to manually delete the vectordb directory for running from scratch."
        )

    """
      Set of all programs is the set of primitives functions + all skill functions
      
      could swap this to be a dict
    """
    @property
    def programs(self):
        programs = {}
        for type in self.skill_types:
            programs[type] = f"\n{type} code\n"
            for skill_name, entry in self.skills[type].items():
                programs += f"{entry['code']}\n\n"
            for primitives in self.control_primitives[type]:
                programs += f"{primitives}\n\n"
        return programs

    @property
    def skill_types(self):
        return ["pulumi", "ansible"]

    """
    craft(list): -> inventory -> 1 vector db
      add all to buff
      deploy buff

      return InventoryItem

    skill1(buffer):

      Recipe
      -----
      primitveA
      primitiveB
      -----
      
      new_item = craft(recipe) -> Adds state file for each crafted recipe
      
      return new_item

    skill2(buffer):
      primitveA
      primitiveB
      add both to buffer
      deploy buff

      return [a.state, b.state]

    skill3(buffer):
      a = skill1(buffer)
      b = skill2(buffer)

      primitive(a, b, buffer)

    info is a dict. Passes task to filter out the deposit skill
    Creates skill description from name and code (do not include task as task may include additional info?)
    If program name exists, overwrite skill name with new program
        If dumping program, update the version number
    else set dumped name to the target program name

    add skill description to vecor db with id = program name and metadate
    set program name in skills_dict[name] = description, code
    make sure number of skills is same as number of items in vector db
    
    """
    def add_new_pulumi_skill(self, info):
        if info["task"].startswith("Deposit useless items into the chest at"):
            # No need to reuse the deposit skill
            return
        pulumi_program_name = info["pulumi_program_name"]
        pulumi_program_code = info["pulumi_program_code"]

        pulumi_skill_description = self.generate_pulumi_skill_description(pulumi_program_name, pulumi_program_code)
        print(
            f"\033[33mSkill Manager generated description for {pulumi_program_name}:\n{pulumi_skill_description}\033[0m"
        )
        if pulumi_program_name in self.skills["pulumi"]:
            print(f"\033[33mSkill {pulumi_program_name} already exists. Rewriting!\033[0m")
            self.pulumi_vectordb._collection.delete(ids=[pulumi_program_name])
            i = 2
            while f"{pulumi_program_name}V{i}.js" in os.listdir(f"{self.ckpt_dir}/skill/pulumi/code"):
                i += 1
            dumped_program_name = f"{pulumi_program_name}V{i}"
        else:
            dumped_program_name = pulumi_program_name
        self.pulumi_vectordb.add_texts(
            texts=[pulumi_skill_description],
            ids=[pulumi_program_name],
            metadatas=[{"name": pulumi_program_name}],
        )
        self.skills["pulumi"][pulumi_program_name] = {
            "code": pulumi_program_code,
            "description": pulumi_skill_description,
        }
        assert self.pulumi_vectordb._collection.count() == len(
            self.skills["pulumi"]
        ), "vectordb is not synced with skills.json"
        U.dump_text(
            pulumi_program_code, f"{self.ckpt_dir}/skill/pulumi/code/{dumped_program_name}.py"
        )
        U.dump_text(
            pulumi_skill_description,
            f"{self.ckpt_dir}/skill/pulumi/description/{dumped_program_name}.txt",
        )
        U.dump_json(self.skills, f"{self.ckpt_dir}/skill/skills.json")
        self.pulumi_vectordb.persist()

    def add_new_ansible_skill(self, info):
        if info["task"].startswith("Deposit useless items into the chest at"):
            # No need to reuse the deposit skill
            return
        ansible_program_name = info["ansible_program_name"]
        ansible_program_code = info["ansible_program_code"]

        ansible_skill_description = self.generate_ansible_skill_description(ansible_program_name, ansible_program_code)
        print(
            f"\033[33mSkill Manager generated description for {ansible_program_name}:\n{ansible_skill_description}\033[0m"
        )
        if ansible_program_name in self.skills["ansible"]:
            print(f"\033[33mSkill {ansible_program_name} already exists. Rewriting!\033[0m")
            self.ansible_vectordb._collection.delete(ids=[ansible_program_name])
            i = 2
            while f"{ansible_program_name}V{i}.js" in os.listdir(f"{self.ckpt_dir}/skill/ansible/code"):
                i += 1
            dumped_program_name = f"{ansible_program_name}V{i}"
        else:
            dumped_program_name = ansible_program_name
        self.ansible_vectordb.add_texts(
            texts=[ansible_skill_description],
            ids=[ansible_program_name],
            metadatas=[{"name": ansible_program_name}],
        )
        self.skills["ansible"][ansible_program_name] = {
            "code": ansible_program_code,
            "description": ansible_skill_description,
        }
        assert self.ansible_vectordb._collection.count() == len(
            self.skills["ansible"]
        ), "vectordb is not synced with skills.json"
        U.dump_text(
            ansible_program_code, f"{self.ckpt_dir}/skill/ansible/code/{dumped_program_name}.py"
        )
        U.dump_text(
            ansible_skill_description,
            f"{self.ckpt_dir}/skill/ansible/description/{dumped_program_name}.txt",
        )
        U.dump_json(self.skills, f"{self.ckpt_dir}/skill/skills.json")
        self.ansible_vectordb.persist()

    """
    Generates skill description of the code by annotating the code with its goal/purpose
    returns funtion name with skill description attached
    """
    def generate_pulumi_skill_description(self, program_name, program_code):
        messages = [
            SystemMessage(content=load_prompt("skill")),
            HumanMessage(
                content=program_code
                + "\n\n"
                + f"The main function is `{program_name}`."
            ),
        ]
        skill_description = f"    // { self.llm(messages).content}"
        return f"def {program_name}():\n\t{skill_description}\n"

    def generate_ansible_skill_description(self, program_name, program_code):
        messages = [
            SystemMessage(content=load_prompt("skill")),
            HumanMessage(
                content=program_code
                + "\n\n"
                + f"The main function is `{program_name}`."
            ),
        ]
        skill_description = f"    // { self.llm(messages).content}"
        return f"def {program_name}(output):\n\t{skill_description}\n"

    """
    queries the skill vector db for k skills related to the query
    given the k most relavent skills, return a list of them
    """
    def retrieve_skills(self, query):
        ansible_k = min(self.ansible_vectordb._collection.count(), self.retrieval_top_k)
        pulumi_k = min(self.pulumi_vectordb._collection.count(), self.retrieval_top_k)

        print(f"\033[33mSkill Manager retrieving for {ansible_k + pulumi_k} skills\033[0m")
        ansible_docs_and_scores = self.ansible_vectordb.similarity_search_with_score(query, k=ansible_k)
        pulumi_docs_and_scores = self.pulumi_vectordb.similarity_search_with_score(query, k=pulumi_k)

        dscore_list = [ansible_docs_and_scores, pulumi_docs_and_scores]

        print(
            f"\033[33mSkill Manager retrieved skills: "
            f"{''.join([', '.join([doc.metadata['name'] for doc, _ in docs_and_scores]) for docs_and_scores in dscore_list])}\033[0m"
        )

        ansible_skills = []
        for doc, _ in ansible_docs_and_scores:
            ansible_skills.append(self.skills["ansible"][doc.metadata["name"]]["code"])

        pulumi_skills = []
        for doc, _ in pulumi_docs_and_scores:
            pulumi_skills.append(self.skills["pulumi"][doc.metadata["name"]]["code"])

        return pulumi_skills, ansible_skills
