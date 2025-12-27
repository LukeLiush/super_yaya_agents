from invesetment_agent.application.dtos.stock_summarization_dtos import SingleStockSummarizationRequest, \
    MultiStockSummarizationRequest
from invesetment_agent.infrastructure.config.container import Application
from invesetment_agent.infrastructure.config.container import create_application


def main():
    instruction = """
        Format the response as a Slack-friendly message.
        Rules:
        - Use short sections with clear bold headers.
        - Use bullet points for lists.
        - Use Slack-style tables (Markdown tables) when presenting structured data.
        - Use fenced code blocks for logs, commands, or metrics.
        - Keep lines short (avoid long paragraphs).
        - Use emojis sparingly and only when they improve clarity (e.g. ✅ ⚠️ 🚨).
        - Do NOT use HTML.
        - Do NOT include excessive markdown nesting.

        Tone:
        - Clear, concise, and operational.
        - Suitable for posting directly into a Slack channel.
        - Avoid filler text or conversational language.

        If applicable:
        - Start with a 1–2 line summary.
        - Highlight key metrics or outcomes.
        - Clearly call out actions, risks, or next steps. 


        """
    app: Application = create_application()
    stock_summarization_use_case = app.stock_summarization_use_case
    vtsax = SingleStockSummarizationRequest("vtsax")
    vtsax.instructions.append(instruction)
    # vtsax.instructions.append("Format your response using markdown and use tables to display data where possible")
    stock_summarization_use_case.execute(MultiStockSummarizationRequest([vtsax]))
    # vbtlx = SingleStockSummarizationRequest("vbtlx")
    # stock_summarization_use_case.execute(vbtlx)

if __name__ == "__main__":
    main()