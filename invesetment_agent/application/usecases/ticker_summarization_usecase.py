from invesetment_agent.application.dtos.commons import Error, ErrorCode, Result
from invesetment_agent.application.dtos.stock_summarization_dtos import MultiTickerSummarizationRequest
from invesetment_agent.application.exceptions import MultiAgentExecutionError
from invesetment_agent.application.port.ai_agent_service import AgentService


class EquitySummarizationUseCase:
    def __init__(self, agent_service: AgentService):
        self.agent_service = agent_service

    def execute(self, multi_ticker_summarization_request: MultiTickerSummarizationRequest) -> Result:
        answers: list[str] = []
        for single_request in multi_ticker_summarization_request.single_requests:
            try:
                answer: str = self.agent_service.get_answer(
                    query=f"Analyze the ticker {single_request.ticker} to provide a detailed investment report",
                )
                answers.append(answer)
            except MultiAgentExecutionError as e:
                error: Error = Error(
                    message=e.message,
                    code=ErrorCode.AGENT_EXECUTION_ERROR,
                    details={err.agent_name or "Unknown": str(err) for err in e.errors},
                )
                return Result.failure(error)
        return Result.success("\n".join(answers))
