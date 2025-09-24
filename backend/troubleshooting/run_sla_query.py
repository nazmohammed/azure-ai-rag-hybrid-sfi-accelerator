# Run a single SLA pipeline query and print the result
from multiple_data_processing import initialize_sla_rag_pipeline

def main():
    sla = initialize_sla_rag_pipeline()
    query = (
        "Please provide more information about ticket IN0042923: "
        "include the last update, assigned engineer, and current status."
    )
    print("Query:", query)
    resp = sla.run(query)
    print("\n---- Response ----")
    print(resp)
    print("---- End ----")

if __name__ == '__main__':
    main()
