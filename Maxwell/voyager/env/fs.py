from pathlib import Path

import os

def get_folders_and_files(path):
    items = []
    for root, dirs, files in os.walk(str(path)):
        for directory in dirs:
            items.append(os.path.abspath(os.path.join(root, directory)))
        for file in files:
            items.append(os.path.abspath(os.path.join(root, file)))
    return items


class fs:

    def __init__(self,path: str) -> None:
        self.path = Path(path)
        
    def get_user_assets(self) -> list:
        return list(filter(lambda x: "assets" in x,get_folders_and_files(self.path)))
    
    def get_pulumi_stack_state_file(self,stack_name):
        return (self.path / ".pulumi" / stack_name / f"{stack_name}.json").resolve()
    
    def get_env_vars(self):
        return (self.path / ".env").resolve()

print(fs(".").get_env_vars())

    



