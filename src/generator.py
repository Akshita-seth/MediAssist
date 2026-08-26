import os
from dotenv import load_dotenv
from groq import Groq
from embed_store import retrieve
from refusal import is_advice_seeking

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def build_context(retrieved_results):
    documents = retrieved_results['documents'][0]
    metadatas = retrieved_results['metadatas'][0]

    context_lines = []
    for doc, meta in zip(documents, metadatas):
        context_lines.append(f"[Section: {meta['section']}] {doc}")

    return "\n".join(context_lines)


def answer_question(question, source_doc):
    if is_advice_seeking(question):
        return ("I'm not in a position to advise on medical decisions "
                "like dosage changes, whether something is safe, or what "
                "action to take. Please consult your doctor or a licensed "
                "medical professional for guidance on this.")

    retrieved = retrieve(question, source_doc=source_doc, top_k=3)
    context = build_context(retrieved)

    prompt = f"""Context:
{context}

Question: {question}

Answer ONLY using the context above. Cite which section your answer 
came from (e.g. "(Source: LAB RESULTS)"). If the answer isn't in the 
context, say "I don't have that information in this document." Do not 
provide medical advice, diagnosis, or treatment recommendations - only 
explain what is stated in the document."""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    print("--- Blood type question ---")
    print(answer_question("What is the patient's blood type?", source_doc="discharge_01.pdf"))

    print("\n--- Advice question ---")
    print(answer_question("Would it be fine to take another dose?", source_doc="discharge_01.pdf"))