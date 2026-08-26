import json

with open("data/eval_results.json", "r", encoding="utf-8") as f:
    results = json.load(f)

hallucinated = [r for r in results if r.get("hallucinated") == True]

print(f"Found {len(hallucinated)} hallucinated cases\n")

for r in hallucinated:
    print(f"Doc: {r['doc']}")
    print(f"Q: {r['question']}")
    print(f"Expected: {r['expected_answer']}")
    print(f"Got: {r['predicted_answer']}")
    print()