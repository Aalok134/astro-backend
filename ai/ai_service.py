# ai/ai_service.py

import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_ai_response(system_prompt, user_prompt):

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=700,
        temperature=0.6
    )

    return response.choices[0].message.content.strip()