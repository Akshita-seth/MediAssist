import json

with open("data/eval_qa.json") as f:
    qa = json.load(f)

print("Total questions:", len(qa))
