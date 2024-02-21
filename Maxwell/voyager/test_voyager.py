import os
from voyager_entry import Voyager

def main():
    v = Voyager(openai_api_key=os.environ['OPENAI_API_KEY'])
    v._learn()

if __name__ == "__main__":
    main()