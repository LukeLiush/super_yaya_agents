from typing import List

from invesetment_agent.application.dtos.commons import Result, Error, ErrorCode
from invesetment_agent.application.dtos.stock_summarization_dtos import MultiStockSummarizationRequest
from invesetment_agent.application.exceptions import MultiAgentExecutionError
from invesetment_agent.application.port.ai_agent_service import SingleAgentService


class StockSummarizationUseCase:

    def __init__(self, agent_service: SingleAgentService):
        self.agent_service = agent_service

    def execute(self, multi_stock_summarization_request: MultiStockSummarizationRequest) -> Result:
        answers: List[str] = []
        for single_request in multi_stock_summarization_request.single_requests:
            try:
                answer: str = self.agent_service.get_answer(
                    query=f"make a detailed report for an investment trying to invest for {single_request.stock} stock",
                    instructions=single_request.instructions)
                answers.append(answer)
            except MultiAgentExecutionError as e:
                error: Error = Error(message=e.message, code=ErrorCode.AGENT_EXECUTION_ERROR,
                                     details={err.agent_name: err.__str__() for err in e.errors})
                return Result.failure(error)
        return Result.success("\n".join(answers))
