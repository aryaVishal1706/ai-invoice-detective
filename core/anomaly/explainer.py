import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


def _get_client() -> Groq:
    key = os.environ.get("GROQ_API_KEY") or os.environ.get("groq_api_key")
    return Groq(api_key=key)


def explain_risk(invoice_id: str, vendor: str, amount: float,
                 risk_score: int, flags: list) -> tuple[str, str]:
    """
    Call Groq LLM to generate a plain-language explanation of the risk flags.
    Returns (explanation, recommendation).
    """
    if not flags:
        return "No anomalies detected. Invoice appears normal.", "APPROVE"

    flag_summary = "\n".join(
        f"- {f.check}: {f.detail} (Severity: {f.severity})" for f in flags
    )

    prompt = f"""You are a corporate accounts payable fraud analyst.
Analyze the following invoice and explain the risk in 3-4 plain sentences for a finance manager.
End with a one-line recommendation: APPROVE, REVIEW, or HOLD.

Invoice ID : {invoice_id}
Vendor     : {vendor}
Amount     : ₹{amount:,.2f}
Risk Score : {risk_score}/100

Detected Issues:
{flag_summary}

Write the explanation clearly. Do not use technical jargon. End with:
Recommendation: [APPROVE / REVIEW / HOLD]"""

    client = _get_client()
    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=300
    )

    full_text = response.choices[0].message.content.strip()

    # Extract recommendation from last line
    recommendation = "REVIEW"
    for line in full_text.splitlines():
        if line.strip().startswith("Recommendation:"):
            rec = line.split(":", 1)[-1].strip().upper()
            if "HOLD" in rec:
                recommendation = "HOLD"
            elif "APPROVE" in rec:
                recommendation = "APPROVE"
            else:
                recommendation = "REVIEW"
            break

    return full_text, recommendation
