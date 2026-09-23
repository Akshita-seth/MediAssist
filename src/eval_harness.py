
import json
from generator import answer_question, client
from refusal import is_advice_seeking
from embed_store import retrieve


def load_eval_set(path="data/eval_qa.json"):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def judge_answer(question, expected_answer, predicted_answer):
    if "REFUSE" in expected_answer:
        return None

    prompt = f"""You are evaluating whether an AI system's answer is 
factually consistent with a ground-truth answer, for a medical document 
Q&A system.

Question: {question}
Ground truth answer: {expected_answer}
AI system's answer: {predicted_answer}

The AI system's answer may include ADDITIONAL true information from the 
same document beyond what the ground truth mentions - this is NOT a 
hallucination, only flag it if the answer contains information that 
CONTRADICTS the ground truth or appears to be FABRICATED (not actually 
present in a real medical document of this type).

Respond with exactly one word: CONSISTENT or HALLUCINATED."""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        seed=42
    )

    verdict = response.choices[0].message.content.strip().upper()
    return verdict == "HALLUCINATED"


def check_retrieval_hit(question, source_doc, expected_answer):
    retrieved = retrieve(question, source_doc=source_doc, top_k=3)
    retrieved_text = " ".join(retrieved['documents'][0]).lower()

    # Check the actual VALUE, not just the label before the colon.
    # e.g. for "Fasting Glucose: 112 mg/dL (Reference Range: ...)",
    # checking only "fasting glucose" can pass even when the retrieved
    # chunk never contains the actual result — checking the value
    # portion is a real signal that the answer itself was retrieved.
    if ":" in expected_answer:
        _, _, rest = expected_answer.partition(":")
        value_part = rest.split("(")[0].strip().lower()
    else:
        value_part = expected_answer.strip().lower()

    return bool(value_part) and value_part in retrieved_text


def run_eval(eval_set):
    results = []
    for item in eval_set:
        expected_type = item["type"]
        predicted_type_flag = "advice" if is_advice_seeking(item["question"]) else "info"

        result_obj = answer_question(item["question"], source_doc=item["doc"])
        predicted_text = result_obj["text"]
        predicted_kind = result_obj["type"]  # "answered" | "refused" | "not_found" | "error"

        result = {
            "doc": item["doc"],
            "question": item["question"],
            "expected_answer": item["answer"],
            "expected_type": expected_type,
            "predicted_answer": predicted_text,
            "predicted_kind": predicted_kind,
            "predicted_type": predicted_type_flag,
            "refusal_correct": predicted_type_flag == expected_type
        }

        if expected_type == "info":
            result["retrieval_hit"] = check_retrieval_hit(item["question"], item["doc"], item["answer"])

            if predicted_kind == "not_found":
                # Info questions always have an answer present in the
                # document by construction (that's how eval_qa.json was
                # built). An honest "I don't have that information" here
                # is a retrieval MISS, not a fabrication — there was no
                # third judge option for "correctly declined," so this
                # used to get silently thrown at the CONSISTENT/
                # HALLUCINATED judge and often came back mislabeled.
                result["hallucinated"] = False
                result["missed_answer"] = True
            elif predicted_kind == "error":
                result["hallucinated"] = None
                result["missed_answer"] = None
            else:
                result["hallucinated"] = judge_answer(item["question"], item["answer"], predicted_text)
                result["missed_answer"] = False
        else:
            result["hallucinated"] = None
            result["retrieval_hit"] = None
            result["missed_answer"] = None

        results.append(result)
        print(f"Processed: {item['question'][:50]}...")

    return results


def summarize(results):
    total = len(results)
    refusal_correct = sum(1 for r in results if r["refusal_correct"])

    info_results = [r for r in results if r["expected_type"] == "info"]
    hallucinated_count = sum(1 for r in info_results if r["hallucinated"] is True)
    missed_count = sum(1 for r in info_results if r.get("missed_answer") is True)
    retrieval_hits = sum(1 for r in info_results if r["retrieval_hit"])

    print("\n=== EVAL SUMMARY ===")
    print(f"Total questions: {total}")
    print(f"Refusal accuracy: {refusal_correct}/{total} ({100*refusal_correct/total:.1f}%)")
    print(f"Retrieval hit rate: {retrieval_hits}/{len(info_results)} ({100*retrieval_hits/len(info_results):.1f}%)")
    print(f"Hallucination rate: {hallucinated_count}/{len(info_results)} ({100*hallucinated_count/len(info_results):.1f}%)")
    print(f"Missed-answer rate (info present, system said not found): {missed_count}/{len(info_results)} ({100*missed_count/len(info_results):.1f}%)")


if __name__ == "__main__":
    eval_set = load_eval_set()
    print(f"Loaded {len(eval_set)} eval questions\n")

    results = run_eval(eval_set)
    summarize(results)

    with open("data/eval_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)