import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


def pick_llm(level: str):
    """
    Groq is the primary provider.
    Gemini is used as a fallback if Groq fails.
    """

    level = level.lower()

    models = {
        "low": "openai/gpt-oss-20b",
        "medium": "openai/gpt-oss-120b",
        "high": "openai/gpt-oss-120b",
        "claude": "openai/gpt-oss-120b",
    }

    if level not in models:
        raise ValueError(f"Unsupported level: {level}")

    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not groq_key and not gemini_key:
        raise ValueError(
            "Configure GROQ_API_KEY or GEMINI_API_KEY in .env"
        )

    providers = []

    if groq_key:
        providers.append(
            ChatGroq(
                model=models[level],
                temperature=0,
                api_key=groq_key,
            )
        )

    if gemini_key:
        providers.append(
            ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0,
                google_api_key=gemini_key,
            )
        )

    if len(providers) == 1:
        return providers[0]

    return providers[0].with_fallbacks(providers[1:])


if __name__ == "__main__":
    llm = pick_llm("low")
    response = llm.invoke("What is the capital of France?")
    print(response.content)