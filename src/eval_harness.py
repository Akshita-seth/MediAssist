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

Does the AI system's answer contain any claim that CONTRADICTS or is 
NOT SUPPORTED by the ground truth answer? Minor differences in wording 
or phrasing are fine - only flag genuine factual inconsistencies or 
fabricated details.

Respond with exactly one word: CONSISTENT or HALLUCINATED."""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}]
    )

    verdict = response.choices[0].message.content.strip().upper()
    return verdict == "HALLUCINATED"


def check_retrieval_hit(question, source_doc, expected_answer):
    retrieved = retrieve(question, source_doc=source_doc, top_k=3)
    retrieved_text = " ".join(retrieved['documents'][0]).lower()

    key_phrase = expected_answer.split(":")[0].strip().lower()
    return key_phrase in retrieved_text


def run_eval(eval_set):
    results = []
    for item in eval_set:
        expected_type = item["type"]
        predicted_type = "advice" if is_advice_seeking(item["question"]) else "info"
        predicted_answer = answer_question(item["question"], source_doc=item["doc"])

        result = {
            "doc": item["doc"],
            "question": item["question"],
            "expected_answer": item["answer"],
            "expected_type": expected_type,
            "predicted_answer": predicted_answer,
            "predicted_type": predicted_type,
            "refusal_correct": predicted_type == expected_type
        }

        if expected_type == "info":
            result["hallucinated"] = judge_answer(item["question"], item["answer"], predicted_answer)
            result["retrieval_hit"] = check_retrieval_hit(item["question"], item["doc"], item["answer"])
        else:
            result["hallucinated"] = None
            result["retrieval_hit"] = None

        results.append(result)
        print(f"Processed: {item['question'][:50]}...")

    return results


def summarize(results):
    total = len(results)
    refusal_correct = sum(1 for r in results if r["refusal_correct"])

    info_results = [r for r in results if r["expected_type"] == "info"]
    hallucinated_count = sum(1 for r in info_results if r["hallucinated"])
    retrieval_hits = sum(1 for r in info_results if r["retrieval_hit"])

    print("\n=== EVAL SUMMARY ===")
    print(f"Total questions: {total}")
    print(f"Refusal accuracy: {refusal_correct}/{total} ({100*refusal_correct/total:.1f}%)")
    print(f"Retrieval hit rate: {retrieval_hits}/{len(info_results)} ({100*retrieval_hits/len(info_results):.1f}%)")
    print(f"Hallucination rate: {hallucinated_count}/{len(info_results)} ({100*hallucinated_count/len(info_results):.1f}%)")


if __name__ == "__main__":
    eval_set = load_eval_set()
    print(f"Loaded {len(eval_set)} eval questions\n")

    results = run_eval(eval_set)
    summarize(results)

    with open("data/eval_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)