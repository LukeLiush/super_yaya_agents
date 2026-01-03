import streamlit as st

from invesetment_agent.application.dtos.stock_summarization_dtos import (
    MultiTickerSummarizationRequest,
    SingleTickerSummarizationRequest,
)
from invesetment_agent.infrastructure.config.container import create_application

st.set_page_config(layout="wide")

st.title("📈 Investment Analysis Dashboard")
st.caption("Analyze multiple stocks with comprehensive investment insights")

# Initialize application
if "app" not in st.session_state:
    st.session_state.app = create_application()

# Stock input section
st.subheader("Stock Symbols")
col1, col2 = st.columns(2)

with col1:
    stock1 = st.text_input("Stock1", value="VTSAX")
with col2:
    stock2 = st.text_input("Stock2", placeholder="e.g. VBTLX")

# Instructions section
st.subheader("Analysis Instructions")

# Get default instructions from DTO
default_request = SingleTickerSummarizationRequest("dummy")

for i in range(st.session_state.instruction_count):
    default_text = ""
    height = 30
    height = (len(default_text.split("\n")) + 1) * height

    instruction = st.text_area(
        f"Instruction {i + 1}",
        key=f"instruction_{i}",
        value=default_text,
        placeholder="Enter analysis requirement...",
        height=height,
    )

# Collect all non-empty stocks
stocks = [s.upper().strip() for s in [stock1, stock2] if s.strip()]

if stocks:
    if st.button("🔍 Analyze Stocks", type="primary"):
        col1, col2 = st.columns(2)

        for i, symbol in enumerate(stocks):
            with col1 if i == 0 else col2:
                st.subheader(f"📊 {symbol}")
                with st.spinner(f"Analyzing {symbol}..."):
                    try:
                        request: SingleTickerSummarizationRequest = SingleTickerSummarizationRequest(symbol.lower())
                        multi_request = MultiTickerSummarizationRequest([request])
                        result = st.session_state.app.stock_summarization_use_case.execute(multi_request)
                        content = result.value if hasattr(result, "value") else str(result)
                        st.markdown(content, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Error analyzing {symbol}: {e!s}")
else:
    st.info("Enter stock symbols to compare side by side")
