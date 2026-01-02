from dataclasses import dataclass, field
from typing import List

import yfinance


@dataclass(frozen=True)
class SingleEquitySummarizationRequest:
    equity: str

    @property
    def query(self) -> str:
        return f"Analyze the {self.equity} equity and provide a detailed investment report."

    @property
    def instructions(self):
        slack_instruction = \
            """
                    Format the response as a Slack-friendly message.
                    Rules:
                    - BOLD: Use single asterisks (*Text*) NOT double (**Text**).
                    - TABLES: Slack does not support Markdown tables. 
                        - OPTION A: Use a multiline code block (```) with an ASCII-style table.
                        - OPTION B: Use a bold header followed by bulleted key-value pairs (e.g. *Metric:* Value).
                    - EMOJIS: Use standard emoji shortcodes like :white_check_mark: or :warning:. 
                    - BULLETS: Use a single dash (-) or bullet (•).
                    - SECTIONS: Separate topics with a bold header and a newline.
                    - NO HTML: Slack will reject it.
                    
                    Tone:
                    - operational.
                    - Suitable for posting directly into a Slack channel.
                    - Avoid filler text or conversational language.
    
                    If applicable:
                    - Start with a 1–2 line summary.
                    - Highlight key metrics or outcomes.
                    - Clearly call out actions, risks, or next steps. 
                    """
        return []

    def is_valid(self) -> bool:
        try:
            ticker = yfinance.Ticker(self.equity)
            info = ticker.info
            return 'symbol' in info or 'shortName' in info
        except:
            return False


@dataclass(frozen=True)
class MultiEquitySummarizationRequest:
    single_requests: List[SingleEquitySummarizationRequest] = field(default_factory=lambda: [])
