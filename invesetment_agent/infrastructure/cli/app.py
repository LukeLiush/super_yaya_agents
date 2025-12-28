from invesetment_agent.application.dtos.commons import Result
from invesetment_agent.application.dtos.stock_summarization_dtos import SingleStockSummarizationRequest, \
    MultiStockSummarizationRequest
from invesetment_agent.infrastructure.config.container import Application
from invesetment_agent.infrastructure.config.container import create_application


def main():
    app: Application = create_application()
    stock_summarization_use_case = app.stock_summarization_use_case
    vtsax = SingleStockSummarizationRequest("vtsax")
    # vtsax.instructions.append("Format your response using markdown and use tables to display data where possible")
    result: Result = stock_summarization_use_case.execute(MultiStockSummarizationRequest([vtsax]))
    print(result)
    # vbtlx = SingleStockSummarizationRequest("vbtlx")
    # stock_summarization_use_case.execute(vbtlx)


if __name__ == "__main__":
    main()
