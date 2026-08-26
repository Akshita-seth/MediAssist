import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def is_advice_seeking(query):
    prompt = f"""Classify the following question as either INFO or ADVICE.

INFO: asks for a fact directly stated in a medical document (e.g. a lab 
value, a diagnosis, a prescribed medication and its dosage as written).

ADVICE: asks for a medical judgment, recommendation, or decision (e.g. 
whether to change a dose, whether something is safe, what the person 
should do, whether they're at risk).

Question: "{query}"

Respond with exactly one word: INFO or ADVICE."""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}]
    )

    classification = response.choices[0].message.content.strip().upper()
    return classification == "ADVICE"


if __name__ == "__main__":
    print(is_advice_seeking("Would it be fine to take another dose?"))
    print(is_advice_seeking("What was the patient's hemoglobin level?"))