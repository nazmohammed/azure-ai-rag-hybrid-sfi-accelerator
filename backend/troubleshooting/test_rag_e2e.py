# Simple end-to-end test for SLA RAG pipeline
# Saves as backend/troubleshooting/test_rag_e2e.py

import traceback
from multiple_data_processing import initialize_sla_rag_pipeline


def main():
    try:
        print("Initializing SLA RAG pipeline...")
        sla = initialize_sla_rag_pipeline()
        test_query = "What's the status of ticket IN0042923?"
        print(f"Running SLA pipeline with: {test_query}")
        result = sla.run(test_query)
        print("\n---- Pipeline result ----")
        print(result)
        print("---- End result ----\n")
    except Exception as e:
        print("Test failed with exception:")
        traceback.print_exc()


if __name__ == '__main__':
    main()
