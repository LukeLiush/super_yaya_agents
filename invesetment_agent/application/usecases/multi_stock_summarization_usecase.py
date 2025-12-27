from typing import List

from invesetment_agent.application.dtos.commons import Result
from invesetment_agent.application.dtos.stock_summarization_dtos import MultiStockSummarizationRequest
from invesetment_agent.application.port.ai_agent_service import SingleAgentService


class StockSummarizationUseCase:

    def __init__(self, research_agent: SingleAgentService, financial_agent: SingleAgentService):
        self.research_agent = research_agent
        self.financial_agent = financial_agent

    def execute(self, multi_stock_summarization_request: MultiStockSummarizationRequest) -> Result:
        answers: List[str] = []
        #
        # web_agent = Agent(
        #     name="Web Agent",
        #     role="Search the web for information",
        #     model=OpenAIChat(id="gpt-4o"),
        #     tools=[DuckDuckGoTools()],
        #     db=db,
        #     add_history_to_context=True,
        #     markdown=True,
        # )

        for single_request in multi_stock_summarization_request.single_requests:
            answer: str = self.research_agent.get_answer(
                query=f"make a detailed report for an investment trying to invest for {single_request.stock} stock",
                instructions=single_request.instructions)
            answers.append(answer)
        return Result.success("\n".join(answers))
