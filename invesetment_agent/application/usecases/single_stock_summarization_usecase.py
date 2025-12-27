from typing import List

from invesetment_agent.application.dtos.commons import Result
from invesetment_agent.application.dtos.stock_summarization_dtos import MultiStockSummarizationRequest
from invesetment_agent.application.port.ai_agent_service import SingleAgentService


class StockSummarizationUseCase:

    def __init__(self, financial_agent_service: SingleAgentService):
        self.financial_agent_service = financial_agent_service

    def execute(self, multi_stock_summarization_request: MultiStockSummarizationRequest) -> Result:
        answers: List[str] = []
        for single_request in multi_stock_summarization_request.single_requests:
            answer: str = self.financial_agent_service.get_answer(
                query=f"make a detailed report for an investment trying to invest for {single_request.stock} stock",
                instructions=single_request.instructions)
            answers.append(answer)
        return Result.success("\n".join(answers))
