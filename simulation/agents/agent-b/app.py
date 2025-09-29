import os
import time

agent_id = os.getenv('AGENT_ID', 'agent-b')

if __name__ == '__main__':
    while True:
        print(f"{agent_id}: running")
        time.sleep(5)
